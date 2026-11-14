// Independent second recognition engine. Input: an upright PNG; output: JSON.
import Foundation
import Vision

guard CommandLine.arguments.count == 2 else {
    fputs("usage: vision_ocr image.png\n", stderr)
    exit(2)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["en-US"]
request.usesLanguageCorrection = false
let handler = VNImageRequestHandler(url: URL(fileURLWithPath: CommandLine.arguments[1]))
do {
    try handler.perform([request])
    let rows: [[String: Any]] = (request.results ?? []).map { observation in
        let box = observation.boundingBox
        return ["bbox": [box.origin.x, box.origin.y, box.width, box.height],
                "candidates": observation.topCandidates(3).map {
                    ["text": $0.string, "confidence": $0.confidence] as [String: Any]
                }]
    }
    let result: [String: Any] = ["engine": "Apple Vision", "revision": request.revision,
        "language_correction": false,
        "os": ProcessInfo.processInfo.operatingSystemVersionString, "observations": rows]
    let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
    FileHandle.standardOutput.write(data)
} catch {
    fputs("Vision OCR failed: \(error)\n", stderr)
    exit(1)
}
