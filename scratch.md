
Read CLAUDE.md and the docs/ folder to understand the project. Then implement Phase 7: the Tauri + React frontend for LEAF.
Ask any clarifying questions before starting.

---

Phase 6 complete

---

Phase 6 Implementation Summary                                                                                                                                                    
                                                                                                                                                                                    
  New Files Created                                                                                                                                                                 
                                                                                                                                                                                    
  1. src/leaf/mcp/__init__.py - Module exports                                                                                                                                      
  2. src/leaf/mcp/protocol.py - MCP protocol definitions:                                                                                                                           
    - JSON-RPC message types                                                                                                                                                        
    - MCP-specific types (tools, resources, capabilities)                                                                                                                           
  3. src/leaf/mcp/client.py - Stdio-based MCP client:                                                                                                                               
    - Connects to MCP servers via subprocess                                                                                                                                        
    - Handles JSON-RPC communication                                                                                                                                                
    - Async context manager support                                                                                                                                                 
  4. src/leaf/mcp/config.py - Global MCP configuration:                                                                                                                             
    - Server configuration management                                                                                                                                               
    - Persistence to ~/.config/leaf/mcp.json                                                                                                                                        
    - Built-in server definitions (filesystem, fetch, memory)                                                                                                                       
  5. src/leaf/mcp/registry.py - MCP server registry:                                                                                                                                
    - Manages active connections                                                                                                                                                    
    - Singleton pattern                                                                                                                                                             
    - Tool discovery and calling                                                                                                                                                    
  6. src/leaf/mcp/agent_tools.py - PydanticAI integration:                                                                                                                          
    - Dynamic Pydantic model creation from JSON schemas                                                                                                                             
    - MCP tool result model                                                                                                                                                         
    - Tools prompt formatting                                                                                                                                                       
  7. src/leaf/mcp/card_helper.py - Helper for card programs:                                                                                                                        
    - MCPClient class for easy tool access                                                                                                                                          
    - Sync and async tool calling                                                                                                                                                   
  8. src/leaf/api/mcp_routes.py - API endpoints:                                                                                                                                    
    - GET /api/mcp/servers - List servers                                                                                                                                           
    - POST /api/mcp/servers - Add server                                                                                                                                            
    - DELETE /api/mcp/servers/{id} - Remove server                                                                                                                                  
    - POST /api/mcp/servers/{id}/enable|disable|connect|disconnect                                                                                                                  
    - GET /api/mcp/tools - List available tools                                                                                                                                     
    - POST /api/mcp/tools/call - Call a tool                                                                                                                                        
  9. tests/test_phase6.py - 25 tests                                                                                                                                                
                                                                                                                                                                                    
  Modified Files                                                                                                                                                                    
                                                                                                                                                                                    
  1. src/leaf/main.py - Registered MCP routes, added MCP disconnect on shutdown                                                                                                     
  2. src/leaf/agent/leaf_agent.py - Added call_mcp_tool and list_mcp_tools agent tools                                                                                              
                                                                                                                                                                                    
  Key Features                                                                                                                                                                      
                                                                                                                                                                                    
  - stdio-based MCP client: Connects to MCP servers via subprocess stdin/stdout                                                                                                     
  - Global configuration: Servers are configured globally, shared across projects                                                                                                   
  - Built-in servers: Pre-configured servers (filesystem, fetch, memory) using Anthropic's official MCP servers                                                                     
  - Agent integration: Agent can discover and call MCP tools via call_mcp_tool and list_mcp_tools                                                                                   
  - Card helper: Card programs can use from leaf.mcp.card_helper import MCPClient to access MCP tools                                                                               
  - REST API: Full CRUD for managing MCP servers plus tool calling                                                                                                                  
                                                                                                                                                                                    
  Usage Example                                                                                                                                                                     
                                                                                                                                                                                    
  # In a card program                                                                                                                                                               
  from leaf.mcp.card_helper import MCPClient                                                                                                                                        
                                                                                                                                                                                    
  mcp = MCPClient()                                                                                                                                                                 
                                                                                                                                                                                    
  # List available tools                                                                                                                                                            
  for tool in mcp.list_tools():                                                                                                                                                     
      print(f"{tool['server_id']}/{tool['name']}")                                                                                                                                  
                                                                                                                                                                                    
  # Call a tool                                                                                                                                                                     
  result = mcp.call("fetch", "fetch", url="https://example.com")                                                                                                                    
  if result["success"]:                                                                                                                                                             
      print(result["output"])

---
Read CLAUDE.md and context/LEAF_SPEC.md to understand the LEAF project.

Implement Phase 1 (Foundation):
- FastAPI app skeleton with WebSocket support
- SQLite database setup with SQLModel
- Workspace selection and initialization
- Basic project structure

Start with the Python backend. We'll add Tauri and the React frontend after the backend is working. Ask me any questions you have before starting.