import json
from datetime import datetime, timedelta, timezone

from pywebpush import webpush, WebPushException
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.payment import Settlement
from app.models.user import User
from app.models.group import Group


async def send_overdue_reminders() -> None:
    """Send push notifications for debts older than 2 weeks."""
    async with async_session_factory() as db:
        two_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=2)

        result = await db.execute(
            select(Settlement)
            .where(
                Settlement.is_settled == False,
                Settlement.created_at <= two_weeks_ago,
            )
        )
        overdue = result.scalars().all()

        for settlement in overdue:
            # Get debtor's push subscription
            user_result = await db.execute(
                select(User).where(User.id == settlement.from_user)
            )
            debtor = user_result.scalar_one_or_none()
            if not debtor or not debtor.push_subscription:
                continue

            # Get creditor name
            creditor_result = await db.execute(
                select(User).where(User.id == settlement.to_user)
            )
            creditor = creditor_result.scalar_one_or_none()

            # Get group name
            group_result = await db.execute(
                select(Group).where(Group.id == settlement.group_id)
            )
            group = group_result.scalar_one_or_none()

            payload = json.dumps({
                "title": "Splitify Reminder",
                "body": f"You still owe {creditor.display_name if creditor else 'someone'} "
                        f"${settlement.amount} from {group.name if group else 'a group'}. Settle up!",
                "url": f"/groups/{settlement.group_id}",
            })

            try:
                webpush(
                    subscription_info=debtor.push_subscription,
                    data=payload,
                    vapid_private_key=settings.vapid_private_key,
                    vapid_claims={"sub": f"mailto:{settings.vapid_claims_email}"},
                )
            except WebPushException:
                pass  # subscription may be expired
