export interface SlotHoldOut {
  id: number;
  slot_id: number;
  student_id: number;
  expires_at: string;
  status: string | null;
}

export interface RegistrationCreate {
  exam_id: number;
  hold_id: number;
}

export interface PaymentOrderOut {
  payment_id: number;
  order_id: string;
  amount: number;
  currency: string;
  // Null when Razorpay isn't configured for this deployment (local/dev
  // "mock mode" — see backend utils/payments.is_live()). The frontend must
  // branch on this instead of always opening the real Razorpay widget.
  key_id: string | null;
}

export interface PaymentVerifyRequest {
  registration_id: number;
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}
