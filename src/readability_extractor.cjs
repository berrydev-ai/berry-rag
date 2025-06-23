#!/usr/bin/env node
/**
 * Readability Content Extractor
 * Uses Mozilla's Readability library to extract clean content from HTML
 */

const { Readability } = require("@mozilla/readability")
const { JSDOM } = require("jsdom")

function extractContent(html, url = "https://example.com") {
  try {
    // Create JSDOM instance
    const dom = new JSDOM(html, { url })
    const document = dom.window.document

    // Check if content is probably readable
    const { isProbablyReaderable } = require("@mozilla/readability")
    if (!isProbablyReaderable(document)) {
      return {
        success: false,
        error: "Content is not readable",
        readable: false,
      }
    }

    // Extract content using Readability
    const reader = new Readability(document, {
      debug: false,
      charThreshold: 100,
      classesToPreserve: ["highlight", "code", "pre"],
      keepClasses: false,
      serializer: (el) => el.innerHTML,
    })

    const article = reader.parse()

    if (!article) {
      return {
        success: false,
        error: "Failed to parse article",
        readable: false,
      }
    }

    // Extract additional metadata
    const metadata = extractMetadata(document, url)

    // Convert HTML content to markdown-like format
    const textContent = convertToMarkdown(article.content)

    return {
      success: true,
      readable: true,
      article: {
        title: article.title || metadata.title || "Untitled",
        content: article.content,
        textContent: textContent,
        length: article.length,
        excerpt: article.excerpt || metadata.description || "",
        byline: article.byline || metadata.author || "",
        dir: article.dir || "ltr",
        siteName: article.siteName || metadata.siteName || "",
        lang: article.lang || metadata.lang || "en",
        publishedTime: article.publishedTime || metadata.publishedTime || null,
      },
      metadata: metadata,
    }
  } catch (error) {
    return {
      success: false,
      error: error.message,
      readable: false,
    }
  }
}

function extractMetadata(document, url) {
  const metadata = { url }

  // Extract various metadata
  const metaSelectors = {
    title: ["title", "h1", '[property="og:title"]', '[name="twitter:title"]'],
    description: [
      '[name="description"]',
      '[property="og:description"]',
      '[name="twitter:description"]',
    ],
    author: [
      '[name="author"]',
      '[rel="author"]',
      ".author",
      ".byline",
      '[property="article:author"]',
    ],
    siteName: ['[property="og:site_name"]', '[name="application-name"]'],
    publishedTime: [
      '[property="article:published_time"]',
      '[name="date"]',
      "time[datetime]",
      ".date",
    ],
    lang: ["html[lang]", "[lang]"],
  }

  for (const [key, selectors] of Object.entries(metaSelectors)) {
    for (const selector of selectors) {
      const element = document.querySelector(selector)
      if (element) {
        let value = null

        if (element.hasAttribute("content")) {
          value = element.getAttribute("content")
        } else if (element.hasAttribute("datetime")) {
          value = element.getAttribute("datetime")
        } else if (key === "lang" && element.hasAttribute("lang")) {
          value = element.getAttribute("lang")
        } else {
          value = element.textContent?.trim()
        }

        if (value) {
          metadata[key] = value
          break
        }
      }
    }
  }

  return metadata
}

function convertToMarkdown(html) {
  if (!html) return ""

  // Create a temporary DOM to process the HTML
  const dom = new JSDOM(html)
  const document = dom.window.document

  // Convert to markdown-like text
  let markdown = ""

  function processNode(node) {
    if (node.nodeType === 3) {
      // Text node
      return node.textContent
    }

    if (node.nodeType !== 1) return "" // Not an element

    const tagName = node.tagName.toLowerCase()
    let content = ""

    // Process child nodes
    for (const child of node.childNodes) {
      content += processNode(child)
    }

    // Format based on tag type
    switch (tagName) {
      case "h1":
        return `\n# ${content.trim()}\n\n`
      case "h2":
        return `\n## ${content.trim()}\n\n`
      case "h3":
        return `\n### ${content.trim()}\n\n`
      case "h4":
        return `\n#### ${content.trim()}\n\n`
      case "h5":
        return `\n##### ${content.trim()}\n\n`
      case "h6":
        return `\n###### ${content.trim()}\n\n`
      case "p":
        return `${content.trim()}\n\n`
      case "br":
        return "\n"
      case "strong":
      case "b":
        return `**${content}**`
      case "em":
      case "i":
        return `*${content}*`
      case "code":
        return `\`${content}\``
      case "pre":
        return `\n\`\`\`\n${content}\n\`\`\`\n\n`
      case "blockquote":
        return `\n> ${content.trim()}\n\n`
      case "ul":
      case "ol":
        return `\n${content}\n`
      case "li":
        return `• ${content.trim()}\n`
      case "a":
        const href = node.getAttribute("href")
        return href ? `[${content}](${href})` : content
      case "img":
        const src = node.getAttribute("src")
        const alt = node.getAttribute("alt") || "Image"
        return src ? `![${alt}](${src})` : ""
      default:
        return content
    }
  }

  markdown = processNode(document.body || document)

  // Clean up excessive whitespace
  markdown = markdown.replace(/\n{3,}/g, "\n\n")
  markdown = markdown.trim()

  return markdown
}

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2)

  if (args.length < 1) {
    console.error("Usage: node readability_extractor.js <html_content> [url]")
    process.exit(1)
  }

  const html = args[0]
  const url = args[1] || "https://example.com"

  const result = extractContent(html, url)
  console.log(JSON.stringify(result, null, 2))
}

module.exports = { extractContent }
