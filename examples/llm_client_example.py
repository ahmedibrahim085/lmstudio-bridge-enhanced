"""
Example usage of LLMClient class
"""

class LLMClient:
    """A simple example client for interacting with large language models"""
    
    def __init__(self, api_key=None, model="gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.example.com/v1"
    
    def generate_text(self, prompt, max_tokens=100, temperature=0.7):
        """Generate text based on a prompt"""
        # This would normally make an API call
        return f"Generated response to: '{prompt}' using {self.model}"
    
    def chat(self, messages):
        """Handle conversation with the LLM"""
        # This would normally make an API call
        return f"Chat response based on {len(messages)} messages"
    
    def embed(self, text):
        """Generate embeddings for text"""
        # This would normally make an API call
        return [0.1, 0.5, 0.3, 0.9]  # Simplified embedding

# Example usage
if __name__ == "__main__":
    # Initialize the client
    client = LLMClient(api_key="your-api-key-here", model="gpt-4")
    
    # Generate text
    response = client.generate_text(
        prompt="Explain quantum computing in simple terms",
        max_tokens=150,
        temperature=0.5
    )
    print("Text Generation:")
    print(response)
    print()
    
    # Chat interaction
    messages = [
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there! How can I help you?"},
        {"role": "user", "content": "Can you explain quantum computing?"}
    ]
    
    chat_response = client.chat(messages)
    print("Chat Interaction:")
    print(chat_response)
    print()
    
    # Generate embeddings
    embedding = client.embed("Hello world")
    print("Embeddings:")
    print(embedding)