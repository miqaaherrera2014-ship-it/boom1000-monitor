import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from deriv_snapshot import choose_boom1000,clean_candles,utc_iso
import pytest

def test_exact_symbol_new_api():
    active=[
        {'underlying_symbol_name':'Boom 500 Index','underlying_symbol':'BOOM500'},
        {'underlying_symbol_name':'Boom 1000 Index','underlying_symbol':'BOOM1000'},
        {'underlying_symbol_name':'Boom 1000 Index (1s)','underlying_symbol':'BOOM1000_1S'},
    ]
    assert choose_boom1000(active)==('BOOM1000','Boom 1000 Index')

def test_exact_symbol_old_api():
    assert choose_boom1000([{'display_name':'Boom 1000 Index','symbol':'BOOM1000'}])[0]=='BOOM1000'

def test_wrong_symbol_rejected():
    with pytest.raises(ValueError):choose_boom1000([{'underlying_symbol_name':'Crash 1000 Index','underlying_symbol':'CRASH1000'}])

def test_ohlc_sort():
    cs=clean_candles([{'epoch':200,'open':10,'high':13,'low':9,'close':12},{'epoch':100,'open':9,'high':10,'low':8,'close':9.5}])
    assert [x['epoch'] for x in cs]==[100,200]

def test_ohlc_bad_rejected():
    with pytest.raises(ValueError):clean_candles([{'epoch':100,'open':20,'high':10,'low':9,'close':12}])
