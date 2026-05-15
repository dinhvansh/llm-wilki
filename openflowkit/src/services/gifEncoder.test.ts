import { describe, expect, it } from 'vitest';
import { encodeGif } from './gifEncoder';

function createFrame(width: number, height: number, color: [number, number, number]): ImageData {
  const bytes = new Uint8ClampedArray(width * height * 4);
  for (let index = 0; index < width * height; index += 1) {
    const offset = index * 4;
    bytes[offset] = color[0];
    bytes[offset + 1] = color[1];
    bytes[offset + 2] = color[2];
    bytes[offset + 3] = 255;
  }
  return {
    data: bytes,
    width,
    height,
  } as ImageData;
}

describe('gifEncoder', () => {
  it('encodes a valid gif blob header', async () => {
    const blob = encodeGif([
      { imageData: createFrame(2, 2, [255, 0, 0]), delayMs: 400 },
      { imageData: createFrame(2, 2, [0, 0, 255]), delayMs: 400 },
    ]);
    const text = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(reader.error);
      reader.onload = () => {
        const buffer = reader.result as ArrayBuffer;
        resolve(new TextDecoder().decode(buffer.slice(0, 6)));
      };
      reader.readAsArrayBuffer(blob);
    });

    expect(blob.type).toBe('image/gif');
    expect(text).toBe('GIF89a');
  });
});
