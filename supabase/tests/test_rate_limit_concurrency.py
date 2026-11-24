"""Concurrent PostgreSQL integration test for atomic flood-limit accounting."""
from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import unittest


def psql(sql: str) -> str:
    result = subprocess.run(
        ["psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-c", sql],
        check=True,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    return result.stdout.strip()


class RateLimitConcurrencyIntegration(unittest.TestCase):
    def test_exactly_the_configured_number_of_parallel_messages_are_allowed(self):
        group_id = 992470599
        user_id = 992470599
        psql(f"insert into public.groups(id) values ({group_id}) on conflict (id) do nothing")
        psql(
            "delete from public.group_message_rate_limits "
            f"where group_id={group_id} and telegram_user_id={user_id}"
        )

        def consume(_):
            return psql(
                "select public.consume_group_message_rate_limit("
                f"{group_id}, {user_id}, 10, 8)"
            )

        with ThreadPoolExecutor(max_workers=24) as pool:
            outcomes = list(pool.map(consume, range(24)))

        accepted = sum(value.lower() == "t" for value in outcomes)
        rejected = sum(value.lower() == "f" for value in outcomes)
        self.assertEqual(accepted, 8, f"expected exactly 8 accepted, got {accepted}: {outcomes}")
        self.assertEqual(rejected, 16, f"expected 16 rejected, got {rejected}: {outcomes}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
