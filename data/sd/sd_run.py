#!/usr/bin/env python3
"""Stable Diffusion (AI Hub precompiled QNN ONNX, w8a16) on the IQ-9075 NPU.

Follows qai_hub_models/models/templates/diffusion/app.py:
classifier-free guidance with two UNet calls per step, Euler for SD 1.5
(AI Hub swaps PNDM for Euler), DDIM v-prediction for SD 2.1, 512x512.
No PyTorch: numpy schedulers, transformers only for the CLIP tokenizer.
"""
import argparse, json, os, sys, time
import numpy as np
import onnxruntime as ort
import onnxruntime_qnn as oq
from PIL import Image
from transformers import CLIPTokenizer

p = argparse.ArgumentParser()
p.add_argument("--model", choices=["sd15", "sd21"], required=True)
p.add_argument("--prompts", required=True, help="JSON list of {id, prompt}")
p.add_argument("--steps", type=int, default=20)
p.add_argument("--guidance", type=float, default=7.5)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--out", default="out")
p.add_argument("--runs", type=int, default=1)
a = p.parse_args()

HOME = os.path.expanduser("~")
MDIR = {"sd15": f"{HOME}/sd/stable_diffusion_v1_5-precompiled_qnn_onnx-w8a16-qualcomm_qcs9075",
        "sd21": f"{HOME}/sd/stable_diffusion_v2_1-precompiled_qnn_onnx-w8a16-qualcomm_qcs9075"}[a.model]
tok = CLIPTokenizer.from_pretrained(f"{HOME}/sd/tok/{a.model}/tokenizer")

# QNN dlopens libQnnHtpV73Stub.so by bare name and the DSP looks for the Skel in
# ADSP_LIBRARY_PATH, so both must point at the wheel's folder before the process starts.
# Ubuntu ships only libcdsprpc.so.1, so ~/sd/lib holds a libcdsprpc.so symlink to it.
_qnn_dir = os.path.dirname(oq.get_library_path())
_rpc_dir = os.path.expanduser("~/sd/lib")
if _qnn_dir not in os.environ.get("LD_LIBRARY_PATH", "").split(":"):
    os.environ["LD_LIBRARY_PATH"] = ":".join([_qnn_dir, _rpc_dir, os.environ.get("LD_LIBRARY_PATH", "")])
    os.environ["ADSP_LIBRARY_PATH"] = _qnn_dir
    os.execv(sys.executable, [sys.executable] + sys.argv)
ort.register_execution_provider_library(oq.get_ep_name(), oq.get_library_path())
devs = [d for d in ort.get_ep_devices() if d.ep_name == oq.get_ep_name()]

META = json.load(open(f"{MDIR}/metadata.json"))["model_files"]
SESS_FILE = {}

def load(component):
    path = f"{MDIR}/{component}.onnx"
    so = ort.SessionOptions()
    so.add_provider_for_devices(devs, {"backend_type": "htp", "htp_performance_mode": "burst"})
    t0 = time.time()
    s = ort.InferenceSession(path, sess_options=so)
    SESS_FILE[id(s)] = f"{component}.onnx"
    print(f"loaded {component}: {os.path.relpath(path, MDIR)} in {time.time()-t0:.1f}s")
    for i in s.get_inputs():
        print("   in ", i.name, i.shape, i.type)
    for o in s.get_outputs():
        print("   out", o.name, o.shape, o.type)
    return s

def qparams(sess, io, name):
    q = META[SESS_FILE[id(sess)]][io][name].get("quantization_parameters")
    return (q["scale"], q["zero_point"]) if q else None

def run(sess, **inputs):
    """Inputs as float arrays by name; uint16 quantize/dequantize from metadata.json."""
    feed = {}
    for name, x in inputs.items():
        q = qparams(sess, "inputs", name)
        feed[name] = x if q is None else np.clip(np.round(x / q[0] + q[1]), 0, 65535).astype(np.uint16)
    out_name = sess.get_outputs()[0].name
    y = sess.run([out_name], feed)[0]
    q = qparams(sess, "outputs", out_name)
    return y if q is None else (y.astype(np.float32) - q[1]) * q[0]

t_load = time.time()
te, unet, vae = load("text_encoder"), load("unet"), load("vae")
t_load = time.time() - t_load

# Scheduler tables (scaled_linear betas, 1000 train steps)
betas = np.linspace(0.00085 ** 0.5, 0.012 ** 0.5, 1000, dtype=np.float64) ** 2
ac = np.cumprod(1.0 - betas)

def euler_schedule(n):  # diffusers EulerDiscrete, timestep_spacing="linspace"
    ts = np.linspace(0, 999, n)[::-1].copy()
    sig_all = np.sqrt((1 - ac) / ac)
    sig = np.interp(ts, np.arange(1000), sig_all)
    return ts, np.append(sig, 0.0)

def ddim_schedule(n):  # diffusers DDIM, timestep_spacing="leading", steps_offset=1
    r = 1000 // n
    return (np.arange(n) * r).round()[::-1].astype(np.int64) + 1, r

def nhwc(x):  # AI Hub latents are channel-last (1, 64, 64, 4)
    return x.transpose(0, 2, 3, 1)

def nchw(x):
    return x.transpose(0, 3, 1, 2)

def generate(prompt, seed):
    timing = {}
    t0 = time.time()
    ids = lambda s: np.array(tok(s, padding="max_length", max_length=tok.model_max_length,
                                 truncation=True).input_ids, dtype=np.int32)[None]
    cond = run(te, tokens=ids(prompt))
    uncond = run(te, tokens=ids(""))
    timing["text_s"] = time.time() - t0

    rng = np.random.default_rng(seed)
    x = rng.standard_normal((1, 4, 64, 64))
    t1 = time.time()
    if a.model == "sd15":
        ts, sig = euler_schedule(a.steps)
        x = x * sig[0]  # init_noise_sigma = max sigma for linspace spacing
        for i, t in enumerate(ts):
            xin = (x / np.sqrt(sig[i] ** 2 + 1)).astype(np.float32)
            tt = np.array([[t]], dtype=np.float32)
            ec = nchw(run(unet, timestep=tt, latent=nhwc(xin), text_emb=cond))
            eu = nchw(run(unet, timestep=tt, latent=nhwc(xin), text_emb=uncond))
            eps = eu + a.guidance * (ec - eu)
            x = x + eps * (sig[i + 1] - sig[i])
    else:
        ts, r = ddim_schedule(a.steps)
        for t in ts:
            tt = np.array([[t]], dtype=np.float32)
            xin = x.astype(np.float32)
            vc = nchw(run(unet, timestep=tt, latent=nhwc(xin), text_emb=cond))
            vu = nchw(run(unet, timestep=tt, latent=nhwc(xin), text_emb=uncond))
            v = vu + a.guidance * (vc - vu)
            at = ac[t]
            ap = ac[t - r] if t - r >= 0 else ac[0]
            x0 = np.sqrt(at) * x - np.sqrt(1 - at) * v
            eps = np.sqrt(at) * v + np.sqrt(1 - at) * x
            x = np.sqrt(ap) * x0 + np.sqrt(1 - ap) * eps
    timing["unet_s"] = time.time() - t1

    t2 = time.time()
    img = run(vae, latent=nhwc(x.astype(np.float32)))
    timing["vae_s"] = time.time() - t2
    timing["total_s"] = time.time() - t0
    img = img[0]
    if img.shape[0] == 3:
        img = img.transpose(1, 2, 0)
    return Image.fromarray((np.clip(img, 0, 1) * 255).round().astype(np.uint8)), timing

os.makedirs(a.out, exist_ok=True)
prompts = json.load(open(a.prompts))
print(f"model load: {t_load:.1f}s")
print("csv,model,prompt_id,run,steps,guidance,seed,text_s,unet_s,vae_s,total_s")
for item in prompts:
    for r in range(1, a.runs + 1):
        img, tm = generate(item["prompt"], a.seed)
        img.save(f"{a.out}/{a.model}-{item['id']}-r{r}.png")
        print(f"csv,{a.model},{item['id']},{r},{a.steps},{a.guidance},{a.seed},"
              f"{tm['text_s']:.2f},{tm['unet_s']:.2f},{tm['vae_s']:.2f},{tm['total_s']:.2f}", flush=True)
