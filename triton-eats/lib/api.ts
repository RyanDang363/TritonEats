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
  latitude: number | null;
  longitude: number | null;
  reason: string;
}

export async function getRecommendations(
  userId: string,
  latitude: number,
  longitude: number
): Promise<FoodRecommendation[]> {
  const resp = await fetch(`${API_URL}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, latitude, longitude }),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to get recommendations");
  }

  const data = await resp.json();
  return data.recommendations;
}
