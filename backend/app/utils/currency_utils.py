from decimal import Decimal
import hashlib

def compute_shares(amount: Decimal, user_ids: list, seed: str | None = None) -> dict:
    """
    Split amount into shares that sum EXACTLY to amount.
    Works in integer cents to avoid floating point errors.
    
    If seed is provided, it is used to deterministically shuffle the user order
    for remainder distribution. This ensures that 'extra pennies' don't always
    go to the same users (e.g. sorted alphabetically), but are distributed
    fairly across different items.
    
    Args:
        amount: The total amount to split.
        user_ids: List of user IDs (strings or UUIDs) to split among.
        seed: Optional string seed (e.g. item_id) for pseudo-random distribution.
        
    Returns:
        Dictionary mapping user_id to their share (Decimal).
    """
    n = len(user_ids)
    if n == 0:
        return {}
        
    # Convert to cents
    amount_cents = int((amount * 100).to_integral_value())
    
    # Calculate base share and remainder
    base_cents = amount_cents // n
    extra_count = amount_cents % n
    
    # Determine order for distributing extra cents
    if seed:
        # Use hash of seed + user_id to sort, creating a deterministic random order
        def get_hash(uid):
            return hashlib.md5(f"{seed}:{uid}".encode()).hexdigest()
        sorted_ids = sorted(user_ids, key=get_hash)
    else:
        # Fallback to simple sort for consistency if no seed
        sorted_ids = sorted(user_ids, key=str)
        
    # Distribute
    shares = {}
    for i, uid in enumerate(sorted_ids):
        # The first `extra_count` users get 1 extra cent
        cents = base_cents + (1 if i < extra_count else 0)
        shares[uid] = Decimal(cents) / Decimal(100)
        
    return shares


def compute_receipt_shares(line_items_data: list[dict], seed: str | None = None) -> dict:
    """
    Computes exact receipt-level shares by aggregating unrounded fractional shares
    for each user across all line items, then distributing remainder cents on the total sum.
    
    Args:
        line_items_data: List of dictionaries with keys "amount" (Decimal) and "user_ids" (list).
        seed: Optional string seed (e.g. receipt_id) for pseudo-random distribution.
        
    Returns:
        Dictionary mapping user_id to their final receipt-level share (Decimal).
    """
    if not line_items_data:
        return {}
        
    user_exact_totals = {}
    total_receipt_cents = 0
    
    for item in line_items_data:
        amount = item["amount"]
        user_ids = item["user_ids"]
        n_users = len(user_ids)
        
        if n_users == 0:
            continue
            
        exact_share = amount / Decimal(n_users)
        
        for uid in user_ids:
            if uid not in user_exact_totals:
                user_exact_totals[uid] = Decimal("0")
            user_exact_totals[uid] += exact_share
            
        total_receipt_cents += int((amount * Decimal("100")).to_integral_value(rounding="ROUND_DOWN"))

    base_user_cents = {}
    total_base_cents = 0
    all_users = list(user_exact_totals.keys())
    
    for uid in all_users:
        cents_exact = user_exact_totals[uid] * Decimal("100")
        base_cents = int(cents_exact.to_integral_value(rounding="ROUND_DOWN"))
        base_user_cents[uid] = base_cents
        total_base_cents += base_cents

    extra_count = total_receipt_cents - total_base_cents
    
    if seed:
        def get_hash(uid):
            return hashlib.md5(f"{seed}:{uid}".encode()).hexdigest()
        sorted_ids = sorted(all_users, key=get_hash)
    else:
        sorted_ids = sorted(all_users, key=str)
        
    shares = {}
    for i, uid in enumerate(sorted_ids):
        cents = base_user_cents[uid] + (1 if i < extra_count else 0)
        shares[uid] = Decimal(cents) / Decimal("100")
        
    return shares
