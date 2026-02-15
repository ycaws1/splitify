export interface Group {
  id: string;
  name: string;
  invite_code: string;
  base_currency: string;
  created_by: string;
  created_at: string;
  members: GroupMember[];
}

export interface GroupMember {
  user_id: string;
  role: string;
  display_name: string | null;
  joined_at: string;
}

export interface Receipt {
  id: string;
  group_id: string;
  uploaded_by: string;
  image_url: string;
  merchant_name: string | null;
  receipt_date: string | null;
  currency: string;
  exchange_rate: string;
  subtotal: string | null;
  tax: string | null;
  service_charge: string | null;
  total: string | null;
  status: string;
  version: number;
  created_at: string;
  line_items: LineItem[];
}

export interface LineItem {
  id: string;
  description: string;
  quantity: string;
  unit_price: string;
  amount: string;
  sort_order: number;
  assignments: Assignment[];
}

export interface Assignment {
  id: string;
  line_item_id: string;
  user_id: string;
  share_amount: string;
}

export interface BalanceEntry {
  from_user_id: string;
  from_user_name: string;
  to_user_id: string;
  to_user_name: string;
  amount: string;
}
