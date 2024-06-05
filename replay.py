import os
import subprocess
import sys
import json

input_file = sys.argv[1]
print(input_file)

language_server = subprocess.Popen(sys.argv[2:], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def send(method, params, request_id=None):
	rpc = {"jsonrpc": "2.0", "method": method, "params": params}
	if request_id is not None:
		rpc["id"] = request_id
	payload = json.dumps(rpc).encode("utf-8")
	language_server.stdin.write(f"Content-Length: {len(payload)}\r\n".encode("ascii"))
	language_server.stdin.write(b"\r\n")
	language_server.stdin.write(payload)
	language_server.stdin.flush()

def receive():
	content_length = 0
	while True:
		line = language_server.stdout.readline().decode("ascii").strip()
		if line == "":
			break
		if line.startswith("Content-Length: "):
			content_length = int(line[len("Content-Length: "):])
	return json.loads(language_server.stdout.read(content_length))

send("initialize", {"processId": os.getpid(), "clientInfo": {"name": "LSP Replay"}, "capabilities": {"textDocument": {}}}, 1)
print(receive())

with open(input_file, "r") as f:
	for line in f:
		event = json.loads(line)
		if "copilot" not in event["server"] or event["direction"] == 2:
			continue
		params = event["params"]
		del event["params"]
		#print(event)

print("sending shutdown")
send("shutdown", {})
print(receive())

print("sending exit")
send("exit", {})
language_server.wait()
