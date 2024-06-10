import os
import subprocess
import sys
import json

input_file = sys.argv[1]
print(input_file)

LLM_LOG_LEVEL="DEBUG"
language_server = subprocess.Popen(sys.argv[2:], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env={"LLM_LOG_LEVEL": LLM_LOG_LEVEL})

# Copilot: add quotes around the keys
config_params = {
	"model": "codellama:7b",
	"backend": "ollama",
	"url": "http://localhost:11434/api/generate",
	"tokensToClear": ["<EOT>"],
	"requestBody": {"options": {"num_predict": 60, "temperature": 0.2, "top_p": 0.95}},
	"fim": {"enabled": True, "prefix": "<PRE> ", "middle": " <MID>", "suffix": " <SUF>"},
	"contextWindow": 1024,
	"tlsSkipVerifyInsecure": True,
	"ide": "vscode",
	"disableUrlPathCompletion": True,
	"tokenizer_config": {"repository": "codellama/CodeLlama-7b-hf"},
}
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
	print(dir(language_server.stdout))
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
		if "method" not in event:
			print(event)
			continue
		if event["method"].startswith("textDocument/"):
			if "lsp-log" in event["params"]["textDocument"]["uri"]:
				continue
			uri = event["params"]["textDocument"]["uri"]
			if event["method"] == "textDocument/didOpen":
				open_files.add(uri)
				send(event["method"], params)
				print("<<<<", receive())
				print("opened", uri)
				del params["textDocument"]["text"]
				print(params)
			elif event["method"] == "textDocument/didClose":
				if uri in open_files:
					open_files.remove(uri)
					send(event["method"], params)
					print("closed", uri)
			elif event["method"] == "textDocument/didChange":
				if uri in open_files:
					send(event["method"], params)
					# print(event)
					# print("changed", uri)
			else:
				print(i, event)
		elif event["method"] in ("initialize", "initialized"):
			# We do our own initialize
			continue
		elif event["method"].startswith("workspace/"):
			# We don't care about workspace events
			continue
		elif event["method"] in ("checkStatus", "setEditorInfo"):
			# We don't care about this stuff
			continue
		else:
			if "doc" not in params:
				print(event)
			uri = params["doc"]["uri"]
			if "lsp-log" in uri:
				continue
			if event["method"] == "getCompletionsCycling":
				continue
			if uri not in open_files:
				open_files.add(uri)
				fake_params = {"textDocument": {"languageId": params["doc"]["languageId"], "text": params["doc"]["source"], "uri": uri, "version": params["doc"]["version"]}}
				send("textDocument/didOpen", fake_params)
				print(receive())
				print("inject open")
			del event["params"]["doc"]["source"]
			print(i, event)
			completion_params = {
				"position": params["doc"]["position"],
				"textDocument": {
					"uri": uri,
					"version": params["doc"]["version"],
				},
			}
			completion_params.update(config_params)
			print(">>>>", completion_params)
			send("llm-ls/getCompletions", completion_params, request_id=i)
			print("<<<<", receive())
		i += 1
		if i > 10:
			break

print("sending shutdown")
send("shutdown", {})
# print(receive())

# print("sending exit")
# send("exit", {})
# language_server.wait()
