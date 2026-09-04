import pytest
from unittest.mock import patch, MagicMock
from sigui_callback import SiguiSecurityCallbackHandler

def test_sigui_callback_initialization():
    handler = SiguiSecurityCallbackHandler(api_key="test_key", endpoint="http://localhost:8000")
    assert handler.api_key == "test_key"
    assert handler.endpoint == "http://localhost:8000"

def test_sigui_callback_on_tool_start_safe():
    handler = SiguiSecurityCallbackHandler(api_key="test_key", endpoint="http://localhost:8000")
    serialized = {"name": "search_tool"}
    # Should not trigger evaluation for non-financial tool
    handler.on_tool_start(serialized, "python tutorials")

@patch("urllib.request.urlopen")
def test_sigui_callback_blocks_high_risk(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"decision": "BLOCK", "reason": "Drain Star topology detected"}'
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    handler = SiguiSecurityCallbackHandler(api_key="test_key", endpoint="http://localhost:8000", fail_on_block=True)
    serialized = {"name": "transfer_funds"}
    
    with pytest.raises(ValueError) as exc_info:
        handler.on_tool_start(serialized, '{"destination": "0x123", "amount": 500}')
    
    assert "Drain Star topology detected" in str(exc_info.value)
