# Docs

| Document | What it covers |
| --- | --- |
| [hardware-reference.md](hardware-reference.md) | **Start here.** Researched specs for every component, with citations, plus the project assumptions that research corrected. |
| [gate-1-usb-enumeration-test.md](gate-1-usb-enumeration-test.md) | The viability test to run first: video out and two cameras in through one USB-C port. Needs no code. |
| [gate-2-on-device-detection.md](gate-2-on-device-detection.md) | The second viability test: two UVC streams and pupil detection at 120 to 200Hz on the phone. |
| [ir-illumination-and-optics.md](ir-illumination-and-optics.md) | Dark-pupil illumination, safety, and the birdbath reflection problem. |
| [calibration-walkthrough.md](calibration-walkthrough.md) | Running a calibration, what good looks like, diagnosing a bad one. |
| [expected-accuracy.md](expected-accuracy.md) | Predicted accuracy and latency, error sources, what the design does not produce. |
| [slippage-and-drift.md](slippage-and-drift.md) | The known weakness of 2D, why it is accepted, and the defenses. |

Read the hardware reference, then the two gate documents. Everything else assumes the gates pass.
