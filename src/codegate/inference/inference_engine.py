from llama_cpp import Llama


class LlamaCppInferenceEngine():
    _inference_engine = None

    def __new__(cls):
        if cls._inference_engine is None:
            cls._inference_engine = super().__new__(cls)
        return cls._inference_engine

    def __init__(self):
        if not hasattr(self, 'models'):
            self.__models = {}

    async def get_model(self, model_path, embedding=False, n_ctx=512, n_gpu_layers=0):
        if model_path not in self.__models:
            self.__models[model_path] = Llama(
                model_path=model_path, n_gpu_layers=n_gpu_layers, verbose=False, n_ctx=n_ctx,
                embedding=embedding)

        return self.__models[model_path]

    async def generate(self, model_path, prompt, n_ctx=512, n_gpu_layers=0, stream=True):
        model = await self.get_model(model_path=model_path, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers)

        for chunk in model.create_completion(prompt=prompt, stream=stream):
            yield chunk

    async def chat(self, model_path, n_ctx=512, n_gpu_layers=0, **chat_completion_request):
        model = await self.get_model(model_path=model_path, n_ctx=n_ctx,
                                     n_gpu_layers=n_gpu_layers)
        return model.create_completion(**chat_completion_request)

    async def embed(self, model_path, content):
        model = await self.get_model(model_path=model_path, embedding=True)
        return model.embed(content)

    async def close_models(self):
        for _, model in self.__models:
            if model._sampler:
                model._sampler.close()
            model.close()
