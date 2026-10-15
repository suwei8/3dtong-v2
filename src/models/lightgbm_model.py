"""Same inputs/labels as XGBoost for a fair chronological comparison."""
import numpy as np

class LightGBMPredictor:
    name="lightgbm"
    def fit(self,X,Y):
        from lightgbm import LGBMClassifier
        self.models=[]
        for d in range(10):
            m=LGBMClassifier(n_estimators=55,max_depth=3,num_leaves=7,
                             learning_rate=.06,min_child_samples=50,
                             reg_lambda=20,verbosity=-1,n_jobs=2,
                             random_state=2026)
            m.fit(X,Y[:,d])
            self.models.append(m)
        return self
    def predict_proba(self,X):
        return np.column_stack([m.predict_proba(X)[:,1] for m in self.models])
