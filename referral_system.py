def generate_referral_link(bot_username, user_id):
    return f"https://t.me/{bot_username}?start={user_id}"

def get_referral_info(db, user_id):
    try:
        referrals = db.get_referrals(user_id)
        balance = db.get_balance(user_id)
        earned = db.get_earned(user_id)
        return (
            f"👥 Ваши рефералы: {len(referrals)}\n"
            f"💰 Ваш баланс: {balance} руб.\n"
            f"💵 Заработано: {earned} руб.\n\n"
            f"💡 Приглашайте друзей и получайте бонусы!"
        )
    except Exception as e:
        logger.error(f"Ошибка в get_referral_info: {e}")
        return "Произошла ошибка при получении информации."
