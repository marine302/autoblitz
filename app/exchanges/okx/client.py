class OKXClient:
    # ...existing code...

    async def get_balance(self) -> dict:
        """계정의 가용 잔고를 조회합니다.

        Returns:
            dict: 통화별 잔고 정보 (예: {'BTC': {'available': 0.1}})
        """
        try:
            response = await self.private_get('/api/v5/account/balance')

            if not response or 'data' not in response:
                return {}

            balances = {}
            for item in response['data'][0].get('details', []):
                currency = item['ccy']
                available = float(item.get('availBal', 0))
                if available > 0:
                    balances[currency] = {
                        'available': available
                    }
            return balances

        except Exception as e:
            self.logger.error(f"Failed to fetch balance: {str(e)}")
            return {}


class OKXLiveClient(OKXClient):
    # ...existing code...

    async def get_balance(self) -> dict:
        """실거래 계정의 가용 잔고를 조회합니다."""
        try:
            response = await self.private_get('/api/v5/account/balance')
            if not response or 'data' not in response:
                return {}
            balances = {}
            for item in response['data'][0].get('details', []):
                currency = item['ccy']
                available = float(item.get('availBal', 0))
                if available > 0:
                    balances[currency] = {'available': available}
            return balances
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Failed to fetch balance: {str(e)}")
            return {}
