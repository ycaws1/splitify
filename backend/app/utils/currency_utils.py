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
