const API_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

export interface FoodRecommendation {
  name: string;
  dining_hall: string;
  station: string;
  meal_period: string;
  calories: number | null;
  protein_g: number | null;
  total_carbs_g: number | null;
  total_fat_g: number | null;
  price: string | null;
  walking_minutes: number | null;
  scooter_minutes: number | null;
  is_open: boolean;
  latitude: number | null;
  longitude: number | null;
  reason: string;
}

export async function getRecommendations(
  userId: string,
  latitude: number,
  longitude: number,
  craving?: string
): Promise<FoodRecommendation[]> {
  const body: Record<string, unknown> = { user_id: userId, latitude, longitude };
  if (craving?.trim()) body.craving = craving.trim();

  const resp = await fetch(`${API_URL}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to get recommendations");
  }

  const data = await resp.json();
  return data.recommendations;
}

export interface DiningHallStatus {
  name: string;
  is_open: boolean;
}

export async function getDiningHours(): Promise<DiningHallStatus[]> {
  const resp = await fetch(`${API_URL}/dining-hours`);
  if (!resp.ok) return [];
  return resp.json();
}
