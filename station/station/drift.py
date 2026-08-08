class DriftTracker:
    def __init__(self):
        self.data = {}

    def add(self, key, dev, tol):
        self.data.setdefault(key, []).append((dev, tol))
        vals = [d for d, _ in self.data[key]]
        tols = [t for _, t in self.data[key]]
        n = len(vals)
        mu = sum(vals) / n
        spread = max(vals) - min(vals)
        if n >= 5 and abs(mu) > tols[0] / 2:
            return "STOP"
        if n >= 5 and (abs(mu) > tols[0] / 3 or spread > tols[0]):
            return "WARN"
        return ""
