import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
import google.generativeai as genai
from concurrent.futures import TimeoutError
from functools import partial
import json

# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
#client = genai.Client(api_key=api_key)

max_iterations = 6
last_response = None
iteration = 0
iteration_response = []

async def generate_with_timeout(prompt, timeout=10):
    """Generate content with a timeout"""
    print("Starting LLM generation...")
    print("prompt::",prompt)
    try:
        # Convert the synchronous generate_content call to run in a thread
        model = genai.GenerativeModel('gemini-2.0-flash')
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: model.generate_content(
                    prompt
                )
            ),
            timeout=timeout
        )
        print("LLM generation completed")
        return response
    except TimeoutError:
        print("LLM generation timed out!")
        raise
    except Exception as e:
        print(f"Error in LLM generation: {e}")
        raise

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response
    last_response = None
    iteration = 0
    iteration_response = []

async def main():
    reset_state()  # Reset at the start of main
    print("Starting main execution...")
    try:
        # Create a single MCP server connection
        print("Establishing connection to MCP server...")
        server_params = StdioServerParameters(
            command="python",
            args=["paint_mcp.py"]
        )

        async with stdio_client(server_params) as (read, write):
            print("Connection established, creating session...")
            async with ClientSession(read, write) as session:
                print("Session created, initializing...")
                await session.initialize()
                
                # Get available tools
                print("Requesting tool list...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"Successfully retrieved {len(tools)} tools")

                # Create system prompt with available tools
                print("Creating system prompt...")
                print(f"Number of tools: {len(tools)}")
                
                try:
                    # First, let's inspect what a tool object looks like
                    # if tools:
                    #     print(f"First tool properties: {dir(tools[0])}")
                    #     print(f"First tool example: {tools[0]}")
                    
                    tools_description = []
                    for i, tool in enumerate(tools):
                        try:
                            # Get tool properties
                            params = tool.inputSchema
                            desc = getattr(tool, 'description', 'No description available')
                            name = getattr(tool, 'name', f'tool_{i}')
                            
                            # Format the input schema in a more readable way
                            if 'properties' in params:
                                param_details = []
                                for param_name, param_info in params['properties'].items():
                                    param_type = param_info.get('type', 'unknown')
                                    param_details.append(f"{param_name}: {param_type}")
                                params_str = ', '.join(param_details)
                            else:
                                params_str = 'no parameters'

                            tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                            tools_description.append(tool_desc)
                            print(f"Added description for tool: {tool_desc}")
                        except Exception as e:
                            print(f"Error processing tool {i}: {e}")
                            tools_description.append(f"{i+1}. Error processing tool")
                    
                    tools_description = "\n".join(tools_description)
                    print("Successfully created tools description")
                except Exception as e:
                    print(f"Error creating tools description: {e}")
                    tools_description = "Error loading tools"
                
                print("Created system prompt...")
                
                system_prompt = """You are a math agent solving problems in iterations.
                  You have access to various mathematical tools

Available tools:
"""+tools_description+"""
You must respond with EXACTLY ONE line in one of these formats (no additional text) and it should be in json format
and have different json formats:
1. For function calls: {"name":"function_name","expression":"(value1 + value2)/value3"}
2. For function calls (for reasoning): 
        {"name":"function_name",
         "reasoning_type":"type_of_reasoning",
          "steps":[]
        }
2. For final answers:
        {"name":"result",
         "status":"completed"
        }
Important:
- First, show reasoning and identify the type of reasoning used.
- Then, perform the calculation using the 'calculate' tool.
- Immediately after each 'calculate' call, use the 'verify_calculation' tool with the expression and the expected result to check if the calculation was correct.
- Once the FINAL_ANSWER is calculated, print the value in MS paint.
- Once the value is printed, verify the response of the print action (if applicable using 'verify_method_response').
- Once the value is printed and  verify the response using 'verify_method_response'.
- When a function returns a response (other than 'calculate'), use the 'verify_method_response' tool to ensure the response is valid or as expected.
- Only give the final answer when you have completed all necessary calculations and verifications.
- Do not repeat function calls with the same parameters.

Examples:
- FUNCTION_CALL:{"name":"show_reasoning",
                 "reasoning_type":"arithmetic",
                 "steps":["1. First solve the expression inside the first parentheses: 5 + 5",
                        "2. Then divide or multiply the third params : 5+5/2",
                        "3. Then open the ms paint and draw a rectangle",
                        "4. Next add the calculated result inside the rectangle",
                        "5. Finally complete the process"]
                }    
- FUNCTION_CALL:{"name":"calculate",
                 "expression":"5 + 5",
                }
- FUNCTION_CALL:{"name":"verify_calculation",
                 "expression":"5 + 5",
                 "expected":"10"
                 }
- FUNCTION_CALL:{
                "name":"calculate",
                "expression":"(5 + 5)/2"
                }
- FUNCTION_CALL:{"name":"verify_calculation",
                 "expression":"(5 + 5)/2",
                 "expected":"5"
                 }
- FUNCTION_CALL:{"name":"open_paint"}
- FUNCTION_CALL:{"name":"verify_method_response","status":"success"}
- FUNCTION_CALL:{"name":"draw_rectangle_in_paint",
                 "arguments":{"x1":780,"y1":380,"x2":1140,"y2":700}
                }
- FUNCTION_CALL:{"name":"add_text_in_rectangle",
                 "arguments":{"x1":780,"y1":380,"x2":1140,"y2":700,"text":"Final result is 5"}}
- FUNCTION_CALL:{"name":"verify_method_response","status":"success"}
- FUNCTION_CALL:{"name":"send_email","arguments"
                 "arguments":{"email":"mohan.ramadoss91@gmail.com","agent":"agent_calculator","result":"Final value is 5"}}
- FINAL_ANSWER: {"name":"result","status":"completed"}

DO NOT include any explanations or additional text.
since it is automated request use the parameters mentioned in Examples.
Your entire response should be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER:"""

                query = """Solve this problem (10+2)/2. Let's think step by step."""
                print("Starting iteration loop...")
                prompt = f"{system_prompt}\n\nQuery: {query}"
                i = 1
                while i<15:
                     response = await generate_with_timeout(prompt)
                     if not response or not response.text:
                        break
                     
                     
                     response_text = response.text.strip()
                     json_string = response_text.replace("```json", "").replace("```", "").strip()
                     print(f"response::",json_string)
                     if(json_string is None):
                         raise ValueError("Unknown Exception from LLM")
                         break
                     if(json_string):
                         json_response = json.loads(json_string)
                         func_name = json_response.get('name')
                         if(func_name == "show_reasoning"):
                            #func_name= json_response.get('name')
                            params = json_response.get('steps')
                             # Find the matching tool to get its input schema
                            print(f"Calling function {func_name} with params {params}")
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                raise ValueError(f"Unknown tool: {func_name}")
                            
                            calc_result = await session.call_tool(func_name,arguments= {
                                "steps":params
                            })
                            print("result of function:",calc_result.model_dump_json())                            
                            prompt += f"\nAssitant:{json_string}\nUser: Next step?"

                         elif(func_name == "calculate"):
                             params = json_response.get('expression')
                             print("params",params)
                             calc_result = await session.call_tool(func_name, arguments={
                                 "expression":params
                             })
                             result_value = calc_result.content[0].text
                             print("result of function:",calc_result.model_dump_json()) 
                             prompt += f"\n Assitant:{json_string}\n User: Result is {result_value}. Next step?"
                         elif(func_name == "verify_calculation"):
                             params = json_response.get('expression')
                             expected = json_response.get('expected')
                             calc_result = await session.call_tool(func_name, arguments={
                                 "expression":params,
                                 "expected":expected
                             })
                             print("result of function:",calc_result.model_dump_json()) 
                             result_value = calc_result.content[0].text
                             prompt += f"\nAssitant:{json_string}\nUser: {result_value} Verified. Next step?"
                         elif(func_name == "open_paint"):
                             calc_result = await session.call_tool(func_name)
                             result_value = calc_result.content[0].text
                             print("result of function:",calc_result.model_dump_json()) 
                             prompt += f"\nAssitant:{json_string}\n User: {result_value},Next step?"
                         elif(func_name == "verify_method_response"):
                             message = json_response.get('status')
                             await session.call_tool(func_name,arguments={
                               "response": message 
                             })
                             prompt += f"\nAssitant:{json_string}\n User: Verified. Next step?"
                         elif(func_name == "draw_rectangle_in_paint"):
                             arguments = json_response.get('arguments')
                             await session.call_tool(func_name,arguments={
                              "x1":780,
                              "y1":380,
                              "x2":1140,
                              "y2":700   
                             })
                             result_value = calc_result.content[0].text
                             prompt += f"\nAssitant:{json_string}\n User: {result_value} Next step?"
                         elif(func_name == "add_text_in_rectangle"):
                             text_val = json_response.get('text')
                             print(text_val)
                             await session.call_tool(func_name,arguments={
                               "x1":780,
                              "y1":380,
                              "x2":1140,
                              "y2":700,
                               "text":text_val 
                             })
                             result_value = calc_result.content[0].text
                             prompt += f"\nAssitant:{json_string}\nUser: {result_value} Next step?"
                         elif(func_name == "send_email"):
                             arguments = json_response.get('arguments')
                             await session.call_tool(func_name,arguments=arguments)
                             result_value = calc_result.content[0].text
                             prompt += f"\nAssitant:{json_string}\n User: {result_value} Next step?"
                         elif(func_name == "result"):
                             message = json_response.get('status')
                             eval_prompt = """You are a Prompt Evaluation Assistant.
You will receive a prompt written by a student. Your job is to review this prompt and assess how well it supports structured, step-by-step reasoning in an LLM (e.g., for math, logic, planning, or tool use).
Evaluate the prompt on the following criteria:
1. ✅ Explicit Reasoning Instructions
- Does the prompt tell the model to reason step-by-step?
- Does it include instructions like “explain your thinking” or “think before you answer”?
2. ✅ Structured Output Format
- Does the prompt enforce a predictable output format (e.g., FUNCTION_CALL, JSON, numbered steps)?
- Is the output easy to parse or validate?
3. ✅ Separation of Reasoning and Tools
- Are reasoning steps clearly separated from computation or tool-use steps?
- Is it clear when to calculate, when to verify, when to reason?
4. ✅ Conversation Loop Support
- Could this prompt work in a back-and-forth (multi-turn) setting?
- Is there a way to update the context with results from previous steps?
5. ✅ Instructional Framing
- Are there examples of desired behavior or “formats” to follow?
- Does the prompt define exactly how responses should look?
6. ✅ Internal Self-Checks
- Does the prompt instruct the model to self-verify or sanity-check intermediate steps?
7. ✅ Reasoning Type Awareness
- Does the prompt encourage the model to tag or identify the type of reasoning used (e.g., arithmetic, logic, lookup)?
8. ✅ Error Handling or Fallbacks
- Does the prompt specify what to do if an answer is uncertain, a tool fails, or the model is unsure?
9. ✅ Overall Clarity and Robustness
- Is the prompt easy to follow?
- Is it likely to reduce hallucination and drift?
---
Respond with a structured review in this format:json
{
"explicit_reasoning": true,
"structured_output": true,
"tool_separation": true,
"conversation_loop": true,
"instructional_framing": true,
"internal_self_checks": false,
"reasoning_type_awareness": false,
"fallbacks": false,
"overall_clarity": "Excellent structure, but could improve with self-checks and error fallbacks."
}"""                         
                             print("=======Evaluating the prompt==============")
                             prompt_to_check = eval_prompt +"\n\n"+ "prompt:"+system_prompt
                             response = await generate_with_timeout(prompt_to_check)
                             if not response or not response.text:
                                break
                             response_text = response.text.strip()
                             print(f"prompt evaluated result : {response_text}")                            
                             print(f"Agent {message}")
                             break
                         
                     
                     i=i+1
    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reset_state()  # Reset at the end of main

if __name__ == "__main__":
    asyncio.run(main())
    
    
