import json
import aiohttp
from typing import Optional, Dict
from django.conf import settings


class YougileService:
    BASE_URL = "https://yougile.com/api-v2"
    def __init__(self):
        self.api_key = settings.YOUGILE_API_KEY
        self.project_id = settings.YOUGILE_PROJECT_ID
        self.default_column_id = settings.YOUGILE_COLUMN_ID

        if not self.api_key:
            raise ValueError("YOUGILE_API_KEY not configured")
        if not self.project_id:
            raise ValueError("YOUGILE_PROJECT_ID not configured")

    @property
    def _headers(self):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

    async def create_task(self, title, description = None, column_id = None, executor_id = None):
        url = f"{self.BASE_URL}/tasks"

        final_column_id = column_id or self.default_column_id
        if not final_column_id:
            columns = await self.get_project_columns()
            if columns:
                final_column_id = columns[0].get('id')

        if not final_column_id:
            print("Нет column_id")
            return None

        payload = {"title": title, "columnId": final_column_id}

        if description:
            payload["description"] = description
        if executor_id:
            payload["assigned"] = [executor_id]

        print(f"1. URL: {url}")
        print(f"2. Headers: {{")
        print(f"   'Content-Type': 'application/json',")
        print(f"   'Authorization': 'Bearer {self.api_key[:10]}...'")
        print(f"}}")
        print(f"3. Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self._headers, json=payload) as resp:
                response_text = await resp.text()
                print(f"Статус: {resp.status}")
                print(f"Заголовки: {dict(resp.headers)}")
                print(f"Тело: {response_text}")
                if resp.status in (200, 201):
                    try:
                        data = json.loads(response_text)
                        return {'id': data.get('id'), 'title': title, 'url': f"https://yougile.com/app/task/{data.get('id')}"}
                    except:
                        return None
                else:
                    print(f"Ошибка {resp.status}: {response_text}")
                    return None

    async def get_project_columns(self):
        url = f"{self.BASE_URL}/columns"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    all_columns = data.get('content', [])
                    project_columns = [col for col in all_columns if col.get('projectId') == self.project_id]
                    return project_columns
                return []

    async def find_user_by_email(self, email):
        url = f"{self.BASE_URL}/users"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for user in data.get('content', []):
                        if user.get('email') == email:
                            return user.get('id')
                return None