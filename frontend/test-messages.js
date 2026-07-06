// Test script to validate that the YAML scenario is properly registered and can be loaded
import { conversationCache } from "./src/mocks/loader-optimized";
import "./src/mocks/data/messages-optimized"; // Import to register conversations

async function testYamlLoading() {
  console.log("Testing YAML loading functionality...");

  // Check if the aranwen conversation is registered
  console.log("Has chat-aranwen-01:", conversationCache.has("chat-aranwen-01"));

  // Try to load the conversation
  try {
    console.log("Loading chat-aranwen-01...");
    const messages = await conversationCache.get("chat-aranwen-01");

    if (messages) {
      console.log(`Successfully loaded ${messages.length} messages`);
      console.log("First message:", messages[0]?.content?.substring(0, 50) + "...");
      console.log(
        "Last message:",
        messages[messages.length - 1]?.content?.substring(0, 50) + "...",
      );
    } else {
      console.log("No messages found for chat-aranwen-01");
    }
  } catch (error) {
    console.error("Error loading messages:", error);
  }

  // Test pagination
  try {
    console.log("\nTesting pagination...");
    const paginated = await conversationCache.getPaginated("chat-aranwen-01", 1, 5);

    if (paginated) {
      console.log(
        `Paginated result: ${paginated.messages.length} messages, total: ${paginated.total}, hasMore: ${paginated.hasMore}`,
      );
    } else {
      console.log("No paginated result for chat-aranwen-01");
    }
  } catch (error) {
    console.error("Error with pagination:", error);
  }

  // Show cache stats
  console.log("\nCache stats:", conversationCache.getStats());
}

testYamlLoading().catch(console.error);
