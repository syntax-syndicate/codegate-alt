from llama_cpp import Llama

from codegate.codegate_logging import setup_logging


class LlamaCppInferenceEngine:
    """
    A wrapper class for llama.cpp models

    Attributes:
        __inference_engine: Singleton instance of this class
    """

    __inference_engine = None

    def __new__(cls):
        if cls.__inference_engine is None:
            cls.__inference_engine = super().__new__(cls)
        return cls.__inference_engine

    def __init__(self):
        if not hasattr(self, "models"):
            self.__models = {}
            self.__logger = setup_logging()

    def __del__(self):
        self.__close_models()

    async def __get_model(self, model_path, embedding=False, n_ctx=512, n_gpu_layers=0):
        """
        Returns Llama model object from __models if present. Otherwise, the model
        is loaded and added to __models and returned.
        """
        if model_path not in self.__models:
            self.__logger.info(
                f"Loading model from {model_path} with parameters "
                f"n_gpu_layers={n_gpu_layers} and n_ctx={n_ctx}"
            )
            self.__models[model_path] = Llama(
                model_path=model_path,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
                n_ctx=n_ctx,
                embedding=embedding,
            )

        return self.__models[model_path]

    async def chat(self, model_path, n_ctx=512, n_gpu_layers=0, **chat_completion_request):
        """
        Generates a chat completion using the specified model and request parameters.
        """
        model = await self.__get_model(
            model_path=model_path, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers
        )
        return model.create_completion(**chat_completion_request)

    async def embed(self, model_path, content):
        """
        Generates an embedding for the given content using the specified model.
        """
        model = await self.__get_model(model_path=model_path, embedding=True)
        return model.embed(content)

    async def __close_models(self):
        """
        Closes all open models and samplers
        """
        for _, model in self.__models:
            if model._sampler:
                model._sampler.close()
            model.close()
