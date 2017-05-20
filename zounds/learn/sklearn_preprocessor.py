from preprocess import Preprocessor, PreprocessResult
import sklearn.decomposition


class SklearnModel(Preprocessor):
    def __init__(self, model=None, needs=None):
        super(SklearnModel, self).__init__(needs=needs)
        self.model = model

    def _forward_func(self):
        def x(d, model=None):
            return model.transform(d.reshape((d.shape[0], -1)))

        return x

    def _backward_func(self):
        def x(d, model=None, shape=None):
            return model.inverse_transform(d).reshape((-1,) + shape)

        return x

    def _process(self, data):
        data = self._extract_data(data)
        model = self.model.fit(data.reshape((data.shape[0], -1)))
        shape = data.shape[1:]
        op = self.transform(model=model)
        inv_data = self.inversion_data(model=model, shape=shape)
        inv = self.inverse_transform()
        data = op(data)
        model_cls = self.model.__class__.__name__
        yield PreprocessResult(
            data,
            op,
            inversion_data=inv_data,
            inverse=inv,
            name='SklearnModel.{model_cls}'.format(**locals()))


class SparsePCA(SklearnModel):
    def __init__(self, n_components=None, alpha=None, needs=None):
        model = sklearn.decomposition.SparsePCA(
            n_components=n_components, alpha=alpha)
        super(SparsePCA, self).__init__(model=model, needs=needs)

    def _backward_func(self):
        def x(d, model=None, shape=None):
            import numpy as np
            return np.dot(d, model.components_).reshape((-1,) + shape)
        return x
