#!/bin/bash
# Pi 5 rerun: cooldown before each request, thermal state logged every second
cd ~/iq9075-bench
BIN=${BIN:-~/llama.cpp-338/build/bin}
log() { while true; do echo "$(date +%s),$(vcgencmd measure_temp | cut -d= -f2 | tr -d "'C"),$(vcgencmd get_throttled | cut -d= -f2),$(vcgencmd measure_clock arm | cut -d= -f2),$(cat /sys/class/thermal/cooling_device0/cur_state)"; sleep 1; done; }
echo "t,temp_C,throttled,arm_hz,fan_state" > thermal.log
log >> thermal.log &
MON=$!
trap 'kill $MON' EXIT
vcgencmd get_throttled
python3 llm_prompts.py --bin "$BIN" --models models --long prompts/longo.txt --ngl 0 --threads 4 \
    --only Qwen3.5-0.8B-Q4_0 Qwen3-4B-Q4_0 Qwen3.5-4B-Q4_0 --cool-below 50
vcgencmd get_throttled
