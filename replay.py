import os
import subprocess
import sys
import json

input_file = sys.argv[1]
print(input_file)

LLM_LOG_LEVEL="DEBUG"
language_server = subprocess.Popen(sys.argv[2:], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env={"LLM_LOG_LEVEL": LLM_LOG_LEVEL})

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
		print(line)
		if line.startswith("Content-Length: "):
			content_length = int(line[len("Content-Length: "):])
	return json.loads(language_server.stdout.read(content_length))

send("initialize", {"processId": os.getpid(), "clientInfo": {"name": "LSP Replay"}, "capabilities": {"textDocument": {}}}, 1)
print(receive())

open_files = set()

with open(input_file, "r") as f:
	i = 0
	for line in f:
		event = json.loads(line)
		if "copilot" not in event["server"] or event["direction"] == 2:
			continue
		params = event["params"]
		if event["method"].startswith("textDocument/"):
			if "lsp-log" in event["params"]["textDocument"]["uri"]:
				continue
			uri = event["params"]["textDocument"]["uri"]
			if event["method"] == "textDocument/didOpen":
				open_files.add(uri)
				send(event["method"], params)
				print("opened", uri)
			elif event["method"] == "textDocument/didClose":
				if uri in open_files:
					open_files.remove(uri)
					send(event["method"], params)
					print("closed", uri)
			elif event["method"] == "textDocument/didChange":
				if uri in open_files:
					send(event["method"], params)
					print(event)
					print("changed", uri)
				print(event)
			else:
				print(i, event)
		else:
			uri = params["doc"]["uri"]
			if "lsp-log" in uri:
				continue
			if event["method"] == "getCompletionsCycling":
				continue
			del event["params"]["doc"]["source"]
			print(i, event)
		i += 1
		if i > 10:
			break

print("sending shutdown")
send("shutdown", {})
# print(receive())

# print("sending exit")
# send("exit", {})
# language_server.wait()
