import { useEffect, useRef } from "react";
import { Animated, Pressable, View } from "react-native";
import { Colors } from "../constants/colors";

type VoiceStatus = "idle" | "listening" | "thinking" | "speaking" | "error";

interface VoiceOrbProps {
  status: VoiceStatus;
  onPressIn: () => void;
  onPressOut: () => void;
}

function getOrbColor(status: VoiceStatus): string {
  return Colors.voice[status];
}

export function VoiceOrb({ status, onPressIn, onPressOut }: VoiceOrbProps) {
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const glowAnim = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    if (status === "idle") {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.05, duration: 2000, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 2000, useNativeDriver: true }),
        ])
      ).start();
    } else if (status === "listening") {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.15, duration: 600, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 0.95, duration: 600, useNativeDriver: true }),
        ])
      ).start();
      Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, { toValue: 0.8, duration: 600, useNativeDriver: true }),
          Animated.timing(glowAnim, { toValue: 0.4, duration: 600, useNativeDriver: true }),
        ])
      ).start();
    } else if (status === "thinking") {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.08, duration: 400, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 0.98, duration: 400, useNativeDriver: true }),
        ])
      ).start();
    } else if (status === "speaking") {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.12, duration: 300, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 0.95, duration: 300, useNativeDriver: true }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(1);
      glowAnim.setValue(0.4);
    }

    return () => {
      pulseAnim.stopAnimation();
      glowAnim.stopAnimation();
    };
  }, [status]);

  const color = getOrbColor(status);

  return (
    <Pressable onPressIn={onPressIn} onPressOut={onPressOut}>
      <View style={{ width: 200, height: 200, alignItems: "center", justifyContent: "center" }}>
        {/* Outer glow ring */}
        <Animated.View
          style={{
            position: "absolute",
            width: 200,
            height: 200,
            borderRadius: 100,
            backgroundColor: color,
            opacity: glowAnim,
            transform: [{ scale: pulseAnim }],
          }}
        />
        {/* Middle ring */}
        <Animated.View
          style={{
            position: "absolute",
            width: 160,
            height: 160,
            borderRadius: 80,
            backgroundColor: color,
            opacity: 0.3,
            transform: [{ scale: pulseAnim }],
          }}
        />
        {/* Core orb */}
        <Animated.View
          style={{
            width: 120,
            height: 120,
            borderRadius: 60,
            backgroundColor: color,
            transform: [{ scale: pulseAnim }],
            shadowColor: color,
            shadowOffset: { width: 0, height: 0 },
            shadowOpacity: 0.8,
            shadowRadius: 20,
            elevation: 20,
          }}
        />
      </View>
    </Pressable>
  );
}