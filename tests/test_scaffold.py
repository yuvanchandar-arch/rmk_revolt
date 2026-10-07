import numpy as np
import scipy
import pandas as pd
import sklearn
import fastapi
import plotly

def test_environment_scaffold():
    assert np.__version__ is not None
    assert scipy.__version__ is not None
    assert pd.__version__ is not None
    assert sklearn.__version__ is not None
    assert fastapi.__version__ is not None
    assert plotly.__version__ is not None
