from decimal import Decimal
import unittest
import uuid
from collections import defaultdict
from app.utils.currency_utils import compute_shares

class TestCurrencyUtils(unittest.TestCase):
    def test_compute_shares_exact_sum(self):
        """Test that shares always sum exactly to the total amount."""
        amount = Decimal("10.00")
        users = ["u1", "u2", "u3"]
        shares = compute_shares(amount, users)
        total_shares = sum(shares.values())
        self.assertEqual(total_shares, amount)
        
    def test_compute_shares_equal_split(self):
        """Test simple equal split."""
        amount = Decimal("9.00") # Divisible by 3
        users = ["u1", "u2", "u3"]
        shares = compute_shares(amount, users)
        for share in shares.values():
            self.assertEqual(share, Decimal("3.00"))
            
    def test_compute_shares_remainder(self):
        """Test split with remainder."""
        amount = Decimal("10.00") # 3.33, 3.33, 3.34
        users = ["u1", "u2", "u3"]
        shares = compute_shares(amount, users)
        values = sorted(shares.values())
        self.assertEqual(values, [Decimal("3.33"), Decimal("3.33"), Decimal("3.34")])
        self.assertEqual(sum(values), amount)

    def test_random_distribution(self):
        """Test that different seeds distribute the extra cent to different users."""
        amount = Decimal("0.04") # 3 users, 1 cent remainder
        users = ["u1", "u2", "u3"]
        
        # Track who gets the larger share (0.02) vs smaller (0.01)
        # Actually with 0.04 and 3 users: 1 cent each + 1 remainder.
        # Base is 0.01. Extra is 1 cent.
        # So one user gets 0.02, two get 0.01.
        
        counts = defaultdict(int)
        iterations = 100
        
        for i in range(iterations):
            seed = str(uuid.uuid4())
            shares = compute_shares(amount, users, seed=seed)
            for uid, share in shares.items():
                if share == Decimal("0.02"):
                    counts[uid] += 1
        
        # Verify that the "extra cent" was distributed somewhat evenly
        # It shouldn't be that only one user got it all the time
        print(f"Distribution of extra cent over {iterations} runs: {dict(counts)}")
        self.assertTrue(len(counts) > 1, "The extra cent should not always go to the same user")
        
        # Ideal distribution should be close to 33 each
        for uid in users:
            self.assertGreater(counts[uid], 10, "Each user should get the extra cent sometimes")

    def test_consistent_distribution(self):
        """Test that same seed produces same result."""
        amount = Decimal("10.00")
        users = ["u1", "u2", "u3"]
        seed = "test-seed"
        
        shares1 = compute_shares(amount, users, seed=seed)
        shares2 = compute_shares(amount, users, seed=seed)
        self.assertEqual(shares1, shares2)

if __name__ == "__main__":
    unittest.main()
