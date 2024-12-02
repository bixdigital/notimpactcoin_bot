from datetime import datetime, timedelta
from pymongo import MongoClient
from typing import Optional, Dict, Any, List

class Database:
    def __init__(self, mongodb_uri: str):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client.notimpc_bot
        self.users = self.db.users
        self.tasks = self.db.tasks
        self.setup_indexes()

    def setup_indexes(self):
        self.users.create_index("user_id", unique=True)
        self.tasks.create_index([("user_id", 1), ("task_name", 1)])

    def add_user(self, user_id: int, username: str) -> None:
        self.users.update_one(
            {"user_id": user_id},
            {
                "$setOnInsert": {
                    "username": username,
                    "rewards": 1000,  # Initial rewards
                    "spins": 0,
                    "last_spins": [],
                    "referred_by": None,
                    "premium": False,
                    "last_farm_time": None
                }
            },
            upsert=True
        )

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.users.find_one({"user_id": user_id})

    def update_user(self, user_id: int, **kwargs) -> None:
        self.users.update_one(
            {"user_id": user_id},
            {"$set": kwargs}
        )

    def add_referral(self, referrer_id: int, referred_id: int) -> None:
        referred_user = self.get_user(referred_id)
        if referred_user and referred_user.get("referred_by") is None:
            self.users.update_one(
                {"user_id": referred_id},
                {"$set": {"referred_by": referrer_id}}
            )
            
            referrer = self.get_user(referrer_id)
            reward = 500 if referrer.get("premium") else 300
            
            self.users.update_one(
                {"user_id": referrer_id},
                {"$inc": {"rewards": reward}}
            )

    def get_referral_count(self, user_id: int) -> int:
        return self.users.count_documents({"referred_by": user_id})

    def assign_tasks(self, user_id: int) -> None:
        default_tasks = [
            {"name": "Follow Twitter", "description": "Follow our official Twitter account.", "reward": 50},
            {"name": "Join Telegram", "description": "Join our Telegram group for updates.", "reward": 30},
            {"name": "Refer Friends", "description": "Refer at least one friend.", "reward": 100},
            {"name": "Spin 10 Times", "description": "Complete 10 spins.", "reward": 20},
        ]
        
        for task in default_tasks:
            self.tasks.update_one(
                {"user_id": user_id, "task_name": task["name"]},
                {
                    "$setOnInsert": {
                        "task_description": task["description"],
                        "reward": task["reward"],
                        "is_completed": False
                    }
                },
                upsert=True
            )

    def get_tasks(self, user_id: int) -> List[Dict[str, Any]]:
        return list(self.tasks.find({"user_id": user_id}))

    def complete_task(self, user_id: int, task_name: str) -> None:
        task = self.tasks.find_one({"user_id": user_id, "task_name": task_name})
        if task and not task.get("is_completed"):
            self.tasks.update_one(
                {"user_id": user_id, "task_name": task_name},
                {
                    "$set": {"is_completed": True}
                }
            )
            self.users.update_one(
                {"user_id": user_id},
                {"$inc": {"rewards": task["reward"]}}
            )

    def close(self) -> None:
        self.client.close()