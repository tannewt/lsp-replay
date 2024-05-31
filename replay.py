import subprocess
import sys
import json

input_file = sys.argv[1]
print(input_file)

language_server = subprocess.Popen(sys.argv[2:], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

with open(input_file, "r") as f:
	for line in f:
		event = json.loads(line)
		if "copilot" not in event["server"] or event["direction"] == 2:
			continue
		params = event["params"]
		del event["params"]
		print(event)
