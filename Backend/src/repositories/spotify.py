from datetime import datetime

from core.database import get_db_connection


class SpotifyRepository:
    def get_tokens(self) -> dict | None:
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT access_token, refresh_token, expires_at FROM spotify_tokens WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        return {
            "access_token": row["access_token"],
            "refresh_token": row["refresh_token"],
            "expires_at": row["expires_at"],
        }

    def save_tokens(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
    ) -> None:
        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO spotify_tokens (id, access_token, refresh_token, expires_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    access_token  = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    expires_at    = excluded.expires_at
                """,
                (access_token, refresh_token, expires_at.isoformat()),
            )

    def clear_tokens(self) -> None:
        with get_db_connection() as connection:
            connection.execute("DELETE FROM spotify_tokens WHERE id = 1")
