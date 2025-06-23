#!/usr/bin/env node

/**
 * BerryRAG Vector Database MCP Server
 * Provides vector database access via Model Context Protocol
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  CallToolResult,
  Tool,
  TextContent
} from '@modelcontextprotocol/sdk/types.js';

import { spawn } from 'child_process';
import * as fs from 'fs/promises';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

interface RAGStats {
  document_count: number;
  chunk_count: number;
  embedding_provider: string;
  embedding_dimension: number;
  total_storage_mb: number;
  storage_path: string;
}

class BerryRAGMCPServer {
  private server: Server;
  private pythonPath: string;
  private ragSystemPath: string;
  private integrationPath: string;

  constructor() {
    // Determine paths relative to the project root
    const projectRoot = path.resolve(__dirname, '..');
    this.pythonPath = 'python3';  // Adjust if needed
    this.ragSystemPath = path.join(projectRoot, 'src', 'rag_system.py');
    this.integrationPath = path.join(projectRoot, 'src', 'playwright_integration.py');

    this.server = new Server(
      {
        name: 'berry-rag',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
  }

  private async executePythonScript(scriptPath: string, args: string[]): Promise<string> {
    return new Promise((resolve, reject) => {
      const process = spawn(this.pythonPath, [scriptPath, ...args], {
        cwd: path.dirname(this.ragSystemPath),
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      process.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      process.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      process.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Python script failed with code ${code}: ${stderr}`));
        } else {
          resolve(stdout.trim());
        }
      });

      process.on('error', (error) => {
        reject(error);
      });
    });
  }

  private setupToolHandlers(): void {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'add_document',
          description: 'Add a document to the vector database from scraped content',
          inputSchema: {
            type: 'object',
            properties: {
              url: { 
                type: 'string', 
                description: 'Source URL of the document' 
              },
              title: { 
                type: 'string', 
                description: 'Title of the document' 
              },
              content: { 
                type: 'string', 
                description: 'Content to be vectorized and stored' 
              },
              metadata: { 
                type: 'object', 
                description: 'Additional metadata (optional)' 
              }
            },
            required: ['url', 'title', 'content']
          }
        },
        {
          name: 'search_documents',
          description: 'Search the vector database for similar content',
          inputSchema: {
            type: 'object',
            properties: {
              query: { 
                type: 'string', 
                description: 'Search query to find relevant documents' 
              },
              top_k: { 
                type: 'number', 
                description: 'Number of results to return (default: 5)', 
                default: 5 
              }
            },
            required: ['query']
          }
        },
        {
          name: 'get_context',
          description: 'Get formatted context for a query (optimized for Claude)',
          inputSchema: {
            type: 'object',
            properties: {
              query: { 
                type: 'string', 
                description: 'Query to get relevant context for' 
              },
              max_chars: { 
                type: 'number', 
                description: 'Maximum characters in response (default: 4000)', 
                default: 4000 
              }
            },
            required: ['query']
          }
        },
        {
          name: 'list_documents',
          description: 'List all documents in the vector database',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        },
        {
          name: 'get_stats',
          description: 'Get vector database statistics and health info',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        },
        {
          name: 'process_scraped_files',
          description: 'Process new scraped files from Playwright into the vector database',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        },
        {
          name: 'save_scraped_content',
          description: 'Save content from Playwright scraping for later processing',
          inputSchema: {
            type: 'object',
            properties: {
              url: { 
                type: 'string', 
                description: 'Source URL' 
              },
              title: { 
                type: 'string', 
                description: 'Page title' 
              },
              content: { 
                type: 'string', 
                description: 'Scraped content' 
              },
              suggested_filename: { 
                type: 'string', 
                description: 'Optional filename suggestion' 
              }
            },
            required: ['url', 'title', 'content']
          }
        }
      ] as Tool[]
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        const { name, arguments: args } = request.params;

        switch (name) {
          case 'add_document':
            return await this.handleAddDocument(args);
          
          case 'search_documents':
            return await this.handleSearchDocuments(args);
          
          case 'get_context':
            return await this.handleGetContext(args);
          
          case 'list_documents':
            return await this.handleListDocuments();
          
          case 'get_stats':
            return await this.handleGetStats();
          
          case 'process_scraped_files':
            return await this.handleProcessScrapedFiles();
          
          case 'save_scraped_content':
            return await this.handleSaveScrapedContent(args);

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        console.error(`Tool ${request.params.name} failed:`, error);
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error instanceof Error ? error.message : String(error)}`
            } as TextContent
          ],
          isError: true
        };
      }
    });
  }

  private async handleAddDocument(args: any): Promise<CallToolResult> {
    // Write content to temporary file
    const tempFile = path.join('/tmp', `temp_content_${Date.now()}.txt`);
    await fs.writeFile(tempFile, args.content, 'utf-8');
    
    try {
      const result = await this.executePythonScript(this.ragSystemPath, [
        'add', args.url, args.title, tempFile
      ]);
      
      return {
        content: [
          {
            type: 'text',
            text: `✅ Document added successfully!\n${result}`
          } as TextContent
        ]
      };
    } finally {
      // Clean up temp file
      try {
        await fs.unlink(tempFile);
      } catch (e) {
        // Ignore cleanup errors
      }
    }
  }

  private async handleSearchDocuments(args: any): Promise<CallToolResult> {
    const result = await this.executePythonScript(this.ragSystemPath, [
      'search', args.query
    ]);
    
    return {
      content: [
        {
          type: 'text',
          text: result || 'No results found'
        } as TextContent
      ]
    };
  }

  private async handleGetContext(args: any): Promise<CallToolResult> {
    const result = await this.executePythonScript(this.ragSystemPath, [
      'context', args.query
    ]);
    
    return {
      content: [
        {
          type: 'text',
          text: result || 'No context found'
        } as TextContent
      ]
    };
  }

  private async handleListDocuments(): Promise<CallToolResult> {
    const result = await this.executePythonScript(this.ragSystemPath, ['list']);
    
    return {
      content: [
        {
          type: 'text',
          text: result || 'No documents found'
        } as TextContent
      ]
    };
  }

  private async handleGetStats(): Promise<CallToolResult> {
    const result = await this.executePythonScript(this.ragSystemPath, ['stats']);
    
    return {
      content: [
        {
          type: 'text',
          text: result
        } as TextContent
      ]
    };
  }

  private async handleProcessScrapedFiles(): Promise<CallToolResult> {
    const result = await this.executePythonScript(this.integrationPath, ['process']);
    
    return {
      content: [
        {
          type: 'text',
          text: `🔄 Processing complete!\n${result}`
        } as TextContent
      ]
    };
  }

  private async handleSaveScrapedContent(args: any): Promise<CallToolResult> {
    const scriptArgs = [
      'save', 
      args.url, 
      args.title, 
      args.content
    ];
    
    if (args.suggested_filename) {
      scriptArgs.push(args.suggested_filename);
    }
    
    const result = await this.executePythonScript(this.integrationPath, scriptArgs);
    
    return {
      content: [
        {
          type: 'text',
          text: `💾 Content saved!\n${result}`
        } as TextContent
      ]
    };
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    
    // Log to stderr so it doesn't interfere with MCP communication
    console.error('🍓 BerryRAG MCP Server running on stdio');
    console.error(`📁 RAG System: ${this.ragSystemPath}`);
    console.error(`🔧 Integration: ${this.integrationPath}`);
  }
}

// Start the server
const server = new BerryRAGMCPServer();
server.run().catch((error) => {
  console.error('Failed to start BerryRAG MCP Server:', error);
  process.exit(1);
});
