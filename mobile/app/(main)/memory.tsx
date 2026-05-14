import React, { useState } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../services/api";

interface Memory {
  id: string;
  content: string;
  memory_type: string;
  importance: number;
  created_at: string;
}

export default function MemoryScreen() {
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["memories", search],
    queryFn: async () => {
      const params = search ? `?search=${encodeURIComponent(search)}` : "";
      const res = await api.get<{ memories: Memory[] }>(`/memory${params}`);
      return res.memories;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/memory/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["memories"] }),
    onError: () => Alert.alert("Error", "Failed to delete memory."),
  });

  const confirmDelete = (id: string) => {
    Alert.alert("Delete Memory", "Remove this memory permanently?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: () => deleteMutation.mutate(id),
      },
    ]);
  };

  const typeColor: Record<string, string> = {
    fact: "bg-blue-500",
    preference: "bg-purple-500",
    context: "bg-green-500",
    skill: "bg-yellow-500",
  };

  const renderItem = ({ item }: { item: Memory }) => (
    <View className="bg-gray-800 rounded-2xl p-4 mb-3 mx-4">
      <View className="flex-row items-center justify-between mb-2">
        <View
          className={`px-2 py-0.5 rounded-full ${typeColor[item.memory_type] ?? "bg-gray-600"}`}
        >
          <Text className="text-white text-xs font-semibold capitalize">
            {item.memory_type}
          </Text>
        </View>
        <View className="flex-row items-center gap-2">
          <Text className="text-gray-400 text-xs">
            ★ {item.importance.toFixed(1)}
          </Text>
          <TouchableOpacity onPress={() => confirmDelete(item.id)}>
            <Text className="text-red-400 text-xs font-medium">Delete</Text>
          </TouchableOpacity>
        </View>
      </View>
      <Text className="text-white text-sm leading-5">{item.content}</Text>
      <Text className="text-gray-500 text-xs mt-2">
        {new Date(item.created_at).toLocaleDateString()}
      </Text>
    </View>
  );

  return (
    <SafeAreaView className="flex-1 bg-gray-950">
      <View className="px-4 pt-2 pb-4">
        <Text className="text-white text-2xl font-bold mb-4">Memory</Text>
        <TextInput
          className="bg-gray-800 text-white rounded-xl px-4 py-3 text-sm"
          placeholder="Search memories..."
          placeholderTextColor="#6b7280"
          value={search}
          onChangeText={setSearch}
          returnKeyType="search"
        />
      </View>

      {isLoading ? (
        <ActivityIndicator color="#6366f1" className="mt-10" />
      ) : (
        <FlatList
          data={data ?? []}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={refetch}
              tintColor="#6366f1"
            />
          }
          ListEmptyComponent={
            <Text className="text-gray-500 text-center mt-16">
              No memories found.
            </Text>
          }
          contentContainerStyle={{ paddingBottom: 24 }}
        />
      )}
    </SafeAreaView>
  );
}