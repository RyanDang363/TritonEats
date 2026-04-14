import { Stack, useRouter } from "expo-router";
import { HeaderBackButton } from "@react-navigation/elements";
import { useAuth } from "@/context/AuthContext";
import Colors from "@/constants/Colors";

export default function SurveyLayout() {
  const router = useRouter();
  const { hasProfile, refreshProfile } = useAuth();

  const handleBack = async () => {
    await refreshProfile();
    router.replace("/(tabs)");
  };

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: Colors.navy },
        headerTintColor: "#FFFFFF",
        headerTitleStyle: { fontWeight: "700", fontSize: 16 },
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen
        name="allergies"
        options={{
          title: "Step 1 of 3: Allergies",
          headerLeft: hasProfile === false
            ? () => <HeaderBackButton tintColor="#FFFFFF" onPress={handleBack} />
            : undefined,
        }}
      />
      <Stack.Screen name="diet" options={{ title: "Step 2 of 3: Diet" }} />
      <Stack.Screen name="fitness" options={{ title: "Step 3 of 3: Goals", headerBackTitle: " " }} />
    </Stack>
  );
}
