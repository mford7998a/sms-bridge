import aiohttp
from typing import Dict, List
import json

class SMSHubClient:
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url
        self._session = None

    @property
    async def session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'SMSBridge/1.0',
                    'Content-Encoding': 'gzip'
                }
            )
        return self._session

    async def report_services(self, numbers: Dict[str, Dict]):
        """Report available numbers to SMSHUB"""
        payload = {
            "action": "GET_SERVICES",
            "key": self.api_key,
            "countryList": [
                {
                    "country": "russia",
                    "operatorMap": numbers
                }
            ]
        }
        
        client = await self.session
        async with client.post(
            f"{self.base_url}/services",
            json=payload
        ) as resp:
            return await resp.json()

    async def push_sms(self, sms_id: int, phone: str, 
                      phone_from: str, text: str) -> bool:
        """Push received SMS to SMSHUB"""
        payload = {
            "action": "PUSH_SMS",
            "key": self.api_key,
            "smsId": sms_id,
            "phone": phone,
            "phoneFrom": phone_from,
            "text": text
        }

        client = await self.session
        async with client.post(
            f"{self.base_url}/sms",
            json=payload
        ) as resp:
            response = await resp.json()
            return response["status"] == "SUCCESS"

    async def close(self):
        """Close the client session"""
        if self._session:
            await self._session.close()
            self._session = None