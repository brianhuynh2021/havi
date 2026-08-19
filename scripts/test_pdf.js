const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setContent('<html><body><h1>Test Havi PDF</h1></body></html>');
  const outPath = path.join(__dirname, '..', 'test_out.pdf');
  await page.pdf({ path: outPath, format: 'A4' });
  await browser.close();
  console.log('PDF generated successfully at:', outPath);
  if (fs.existsSync(outPath)) {
    fs.unlinkSync(outPath);
  }
}

main().catch(err => {
  console.error('Error generating PDF:', err);
  process.exit(1);
});
