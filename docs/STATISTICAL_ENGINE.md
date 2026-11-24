# General statistical engine
Synthetic-only explicit in-memory numeric fixtures. No survey/participant input, project-specific variables, automatic hypothesis selection, or cloud data intake.
- OLS Enter, standardized beta, 95% classical and HC3 t intervals, VIF, descriptives, correlations, Breusch–Pagan, Jarque–Bera and maximum Cook's distance.
- Independent NumPy least-squares and HC3 sandwich checks against statsmodels. Not SPSS parity or a substitute for methodological review.
- Reject invalid/nonfinite, rank-deficient, insufficient and near-perfect-fit cases. Missing policy is reject by default; explicit complete-case reports per-variable and total exclusions.
- No automatic deletion based on significance or diagnostics. Negative and null effects retained.
- Test fixtures use deterministic seed; not field data. Real analysis remains gated on approved study protocol and private data handling.
