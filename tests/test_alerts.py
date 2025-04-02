from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from src.handlers.alerts import Alert, check_alerts, price_alerts


@pytest_asyncio.fixture
async def context_mock() -> AsyncGenerator[MagicMock, None]:
    context = MagicMock()
    context.bot = AsyncMock()
    context.job_queue = MagicMock()
    context.job = MagicMock()
    context.job.schedule_removal = MagicMock()
    context.job.user_id = 12345
    context.job.data = Alert(crypto="BTC", direction="above", target_price=50000)
    yield context


@pytest_asyncio.fixture(autouse=True)
def clear_price_alerts() -> Any:
    price_alerts.clear()
    yield
    price_alerts.clear()


@pytest_asyncio.fixture
def mock_get_crypto_price(mocker: Any) -> AsyncMock:
    return mocker.patch("src.utils.get_crypto_price")


@pytest_asyncio.fixture
def mock_safe_send(mocker: Any) -> AsyncMock:
    return mocker.patch("src.utils.safe_send", new_callable=AsyncMock)


@pytest_asyncio.fixture
def mock_get_chat_id(mocker: Any) -> MagicMock:
    return mocker.patch("src.utils.get_chat_id", return_value=111111)


@pytest.mark.asyncio
async def test_alert_triggers_correctly(
    context_mock: MagicMock,
    mock_get_crypto_price: AsyncMock,
    mock_safe_send: AsyncMock,
    mock_get_chat_id: MagicMock,
) -> None:
    mock_get_crypto_price.return_value = 51000

    user_id = context_mock.job.user_id
    alert = Alert(crypto="BTC", direction="above", target_price=50000)
    alert.matches = MagicMock(return_value=True)
    context_mock.job.data = alert
    context_mock.job.chat_id = 111111
    price_alerts[user_id] = [alert]

    mock_get_chat_id.return_value = 111111

    await check_alerts(context_mock)

    mock_safe_send.assert_awaited_once_with(
        context_mock.bot, 111111, text="Alert: BTC is now above €50000 (current price: €51000)."
    )

    assert user_id not in price_alerts
    context_mock.job.schedule_removal.assert_called_once()


@pytest.mark.asyncio
async def test_alert_not_triggered_due_to_price(
    context_mock: MagicMock,
    mock_get_crypto_price: AsyncMock,
    mock_safe_send: AsyncMock,
    mock_get_chat_id: MagicMock,
) -> None:
    mock_get_crypto_price.return_value = 49000  # Below threshold

    user_id = context_mock.job.user_id
    alert = context_mock.job.data
    price_alerts[user_id] = [alert]

    await check_alerts(context_mock)

    mock_safe_send.assert_not_called()
    assert user_id in price_alerts
    context_mock.job.schedule_removal.assert_not_called()


@pytest.mark.asyncio
async def test_price_is_none(
    context_mock: MagicMock,
    mock_get_crypto_price: AsyncMock,
    mock_safe_send: AsyncMock,
    mock_get_chat_id: MagicMock,
) -> None:
    mock_get_crypto_price.return_value = None

    await check_alerts(context_mock)

    mock_safe_send.assert_not_called()
    context_mock.job.schedule_removal.assert_not_called()


@pytest.mark.asyncio
async def test_context_job_is_none(context_mock: MagicMock, mock_safe_send: AsyncMock) -> None:
    context_mock.job = None

    await check_alerts(context_mock)

    mock_safe_send.assert_not_called()


@pytest.mark.asyncio
async def test_context_job_data_is_none(context_mock: MagicMock, mock_safe_send: AsyncMock) -> None:
    context_mock.job.data = None

    await check_alerts(context_mock)

    mock_safe_send.assert_not_called()
