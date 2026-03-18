
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Sequence, Optional

@dataclass
class LinearModel:
    """Tiny linear regression model: y = b0 + sum(bi*xi)

    No numpy dependency. Fit with ordinary least squares using normal equations.
    Good enough for a small starter project (not for large-scale ML).
    """
    coef: List[float]          # length = n_features
    intercept: float

    def predict_one(self, x: Sequence[float]) -> float:
        return self.intercept + sum(c*v for c, v in zip(self.coef, x))

    def predict(self, X: Sequence[Sequence[float]]) -> List[float]:
        return [self.predict_one(x) for x in X]


def _solve_linear_system(A: List[List[float]], b: List[float]) -> List[float]:
    """Solve A x = b with Gaussian elimination (A must be square)."""
    n = len(A)
    # Build augmented matrix
    M = [row[:] + [b_i] for row, b_i in zip(A, b)]

    for col in range(n):
        # Pivot
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-12:
            raise ValueError("Singular matrix in regression fit (try fewer features).")
        M[col], M[pivot] = M[pivot], M[col]

        # Normalize pivot row
        pv = M[col][col]
        for j in range(col, n+1):
            M[col][j] /= pv

        # Eliminate
        for r in range(n):
            if r == col:
                continue
            factor = M[r][col]
            if factor == 0:
                continue
            for j in range(col, n+1):
                M[r][j] -= factor * M[col][j]

    return [M[i][n] for i in range(n)]


def fit_ols(X: List[List[float]], y: List[float]) -> LinearModel:
    """Fit OLS with an intercept by normal equations.

    Adds a column of 1s for the intercept.
    """
    if not X:
        raise ValueError("Empty X")
    n = len(X)
    p = len(X[0])

    # Build design matrix with intercept term
    X1 = [[1.0] + row[:] for row in X]  # n x (p+1)

    # Compute XtX and Xty
    k = p + 1
    XtX = [[0.0]*k for _ in range(k)]
    Xty = [0.0]*k
    for i in range(n):
        xi = X1[i]
        yi = y[i]
        for a in range(k):
            Xty[a] += xi[a] * yi
            for b2 in range(k):
                XtX[a][b2] += xi[a] * xi[b2]

    beta = _solve_linear_system(XtX, Xty)  # length k
    intercept = beta[0]
    coef = beta[1:]
    return LinearModel(coef=coef, intercept=intercept)
