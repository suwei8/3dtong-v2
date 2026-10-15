"""CatBoost multi-label digit occurrence probabilities."""
import numpy as np

class CatBoostPredictor:
    name="catboost"
    def fit(self,X,Y):
        from catboost import CatBoostClassifier
        self.models=[]
        for d in range(10):
            m=CatBoostClassifier(iterations=70,depth=3,learning_rate=.07,
                                  l2_leaf_reg=10,loss_function="Logloss",
                                  random_seed=2026,thread_count=2,verbose=False,
                                  allow_writing_files=False)
            m.fit(X,Y[:,d])
            self.models.append(m)
        return self
    def predict_proba(self,X):
        return np.column_stack([m.predict_proba(X)[:,1] for m in self.models])
