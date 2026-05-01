from app.modules.user_totems.repository import UserTotemRepository


def get_user_totem_repository() -> UserTotemRepository:
    return UserTotemRepository()
