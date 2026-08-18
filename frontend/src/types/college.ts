export interface CollegeCreate {
  name: string;
  code: string;
  logo_url?: string | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
  phone?: string | null;
  email?: string | null;
}

export type CollegeUpdate = Partial<CollegeCreate> & { is_active?: boolean };

export interface CollegeOut {
  id: number;
  name: string;
  code: string;
  logo_url: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  phone: string | null;
  email: string | null;
  is_active: boolean;
}
