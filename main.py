from sglang.utils import launch_server_cmd

from sglang.utils import wait_for_server, print_highlight, terminate_process


server_process, port = launch_server_cmd(
    "python -m sglang.launch_server --model-path D:/model/qwen7b/qwen/Qwen-7B-Chat --host 0.0.0.0"
)

wait_for_server(f"http://localhost:{port}")
print(f"Server started on http://localhost:{port}")


# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# import torch
# from transformers import AutoTokenizer, AutoModelForCausalLM
#
# app = FastAPI()
#
# # 添加根路由作为健康检查接口
# @app.get("/")
# def health_check():
#     return {"status": "ok"}
#
# # 模型加载（请根据实际情况修改模型路径和参数）
# model_path = "D:\\model\\qwen7b\\qwen\\Qwen-7B-Chat"
# tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
# model = AutoModelForCausalLM.from_pretrained(
#     model_path,
#     load_in_8bit=True,
#     device_map="auto",
#     trust_remote_code=True,
# )
#
# # 定义推理请求和响应的数据结构
# class InferenceRequest(BaseModel):
#     prompt: str
#
# class InferenceResponse(BaseModel):
#     generated_text: str
#
# # 推理接口
# @app.post("/inference", response_model=InferenceResponse)
# async def inference(request: InferenceRequest):
#     prompt = request.prompt
#     try:
#         inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
#         with torch.no_grad():
#             outputs = model.generate(**inputs, max_new_tokens=100)
#         generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
#         return InferenceResponse(generated_text=generated_text)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=30000)
