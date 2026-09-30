from collections import defaultdict
import re

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
except Exception:
    TfidfVectorizer = None
    LogisticRegression = None

class LearningEngine:
    """
    Aprende: descriptor HTML del campo -> campo fiscal/ticket interno.
    Usa un modelo ML cuando scikit-learn está disponible y una similitud
    heurística como respaldo.
    """
    def __init__(self, db):
        self.db = db
        self.vectorizer = None
        self.model = None
        self.examples = []
        self.reload()

    def reload(self):
        rows = self.db.get_learning()
        self.examples = [(r["descriptor"], r["target_field"], r["merchant"]) for r in rows]
        self.vectorizer = self.model = None
        if TfidfVectorizer and LogisticRegression and len(set(x[1] for x in self.examples)) >= 2:
            self.vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
            X = self.vectorizer.fit_transform([x[0] for x in self.examples])
            y = [x[1] for x in self.examples]
            self.model = LogisticRegression(max_iter=1000)
            self.model.fit(X, y)

    def learn(self, descriptor, target_field, merchant=""):
        self.db.add_learning(descriptor, target_field, merchant)
        self.reload()

    def predict(self, descriptor):
        if not descriptor:
            return None, 0.0
        desc = descriptor.lower().strip()
        if self.model is not None:
            X = self.vectorizer.transform([descriptor])
            probs = self.model.predict_proba(X)[0]
            idx = probs.argmax()
            return self.model.classes_[idx], float(probs[idx])
        # Respaldo sencillo basado en palabras clave aprendidas.
        scores = defaultdict(int)
        words = set(re.findall(r"[a-záéíóúñü0-9]+", desc))
        for text, field, _ in self.examples:
            overlap = len(words & set(re.findall(r"[a-záéíóúñü0-9]+", text.lower())))
            scores[field] += overlap
        if not scores:
            return None, 0.0
        field, score = max(scores.items(), key=lambda x: x[1])
        return field, min(0.99, 0.25 + score * 0.12)

    def stats(self):
        by_field = defaultdict(int)
        for _, field, _ in self.examples:
            by_field[field] += 1
        return {"examples": len(self.examples), "by_field": dict(by_field)}
