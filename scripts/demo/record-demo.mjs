#!/usr/bin/env node
/**
 * Records the Sotto demo simulation as a GIF.
 *
 * Pipeline: HTML → Playwright (WebM) → ffmpeg (GIF)
 *
 * Usage: node scripts/demo/record-demo.mjs
 */

import { chromium } from 'playwright';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync, mkdirSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const HTML_PATH = join(__dirname, 'demo-simulation.html');
const OUTPUT_DIR = join(__dirname, '..', '..', 'assets');
const VIDEO_PATH = join(OUTPUT_DIR, 'demo-recording.webm');
const GIF_PATH = join(OUTPUT_DIR, 'demo.gif');

// Duration: two full demo cycles ~14s, we capture one cycle + buffer
const RECORD_DURATION_MS = 16000;

async function main() {
  // Ensure output directory exists
  if (!existsSync(OUTPUT_DIR)) {
    mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1200, height: 720 },
    recordVideo: {
      dir: OUTPUT_DIR,
      size: { width: 1200, height: 720 },
    },
    deviceScaleFactor: 2, // Retina quality
  });

  const page = await context.newPage();

  console.log('Loading demo page...');
  await page.goto(`file://${HTML_PATH}`);

  console.log(`Recording for ${RECORD_DURATION_MS / 1000}s...`);
  await page.waitForTimeout(RECORD_DURATION_MS);

  console.log('Stopping recording...');
  await page.close();

  const video = page.video();
  const videoPath = await video.path();

  await context.close();
  await browser.close();

  console.log(`Video saved: ${videoPath}`);

  // Convert to GIF with ffmpeg (two-pass palette for quality)
  console.log('Converting to GIF...');

  const filters = 'fps=15,scale=800:-1:flags=lanczos';
  const paletteCmd = `ffmpeg -y -i "${videoPath}" -vf "${filters},palettegen=stats_mode=diff" -t 15 "${OUTPUT_DIR}/palette.png"`;
  const gifCmd = `ffmpeg -y -i "${videoPath}" -i "${OUTPUT_DIR}/palette.png" -lavfi "${filters} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -t 15 "${GIF_PATH}"`;

  try {
    console.log('  Pass 1: generating palette...');
    execSync(paletteCmd, { stdio: 'pipe' });

    console.log('  Pass 2: rendering GIF...');
    execSync(gifCmd, { stdio: 'pipe' });

    // Clean up temp files
    execSync(`rm -f "${OUTPUT_DIR}/palette.png" "${videoPath}"`, { stdio: 'pipe' });

    // Check file size
    const stats = execSync(`ls -lh "${GIF_PATH}"`).toString().trim();
    console.log(`\nDone! ${stats}`);
    console.log(`\nGIF saved to: ${GIF_PATH}`);
  } catch (err) {
    console.error('ffmpeg conversion failed:', err.message);
    console.log(`Raw video is still available at: ${videoPath}`);
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Recording failed:', err);
  process.exit(1);
});
