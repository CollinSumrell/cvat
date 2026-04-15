CS 4223 Software Quality and Testing - Spring 2026

Ticket 1: Software Test Plan

Wed, April 1, 2026

## **Introduction**

### **Component Overview**

CVAT is an open-source tool for labeling images and videos that are used to train machine learning models. One of its most useful features is the ability to plug in AI models that can automatically generate labels, which saves annotators a lot of manual work. This is handled by the Serverless / AI Model Integration component.

Under the hood, CVAT uses a platform called Nuclio to run these AI models. Each model is packaged inside its own Docker container and exposed as a small HTTP service. The CVAT server finds available models by talking to a Nuclio dashboard, and then sends images to whichever model the user picks and gets annotation results back.

The system supports four kinds of AI functions. Detectors scan an entire image and return bounding boxes or shapes for each object they find. Interactors let the user click on points in an image and return a refined mask. Trackers follow

## **Scope and Objectives**

This document lays out how we plan to test the serverless AI integration component. The scope includes:

- Deploying functions using the provided scripts and the nuctl command-line tool.
- How the CVAT server discovers deployed functions and sends requests to them.
- The request and response format between CVAT and each function type.
- Whether the AI models return correct and usable annotations.
- Speed, resource usage, reliability, and security of the whole pipeline.

## **Assumptions and Constraints**

- We are testing against a local Docker Compose setup using the standard CVAT containers plus the serverless files. Nuclio CLI (nuctl) is on version 1.15.9.
- Tests that need a GPU require an Nvidia card with driver 450.80.02 or newer and the Nvidia Container Toolkit installed.
- This plan focuses on the server-side and container-level integration and does not test the CVAT frontend UI.

# **Quality Attributes and Risks**

## **Selected Quality Attributes**

Ticket 1: Software Test Plan

Wed, April 1, 2026

| Attribute        | Definition                                                                                                           | Relevance                                                                                                                                                                      |
|------------------|----------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Correctness      | The<br>model<br>returns<br>properly<br>formatted<br>results<br>with<br>the<br>right<br>labels<br>and<br>coordinates. | Bad<br>annotations<br>can<br>get<br>into<br>training<br>data<br>and<br>make<br>downstream<br>models<br>worse.                                                                  |
| Reliability      | Functions<br>work<br>consistently<br>without<br>crashing,<br>even<br>if<br>given<br>unusual<br>inputs.               | Annotators<br>depend<br>on<br>these<br>tools<br>being<br>available<br>when<br>they<br>need<br>them                                                                             |
| Performance      | Inference<br>is<br>fast<br>enough<br>for<br>interactive<br>use.                                                      | Slow<br>models<br>waste<br>annotators'<br>time<br>and<br>lower<br>productivity.                                                                                                |
| Interoperability | Functions<br>built<br>with<br>different<br>frameworks<br>all<br>work<br>the<br>same<br>way.                          | CVAT<br>uses<br>models<br>with<br>frameworks<br>like<br>PyTorch,<br>Tensorflow,<br>OpenVINO,<br>etc.,<br>and<br>it's<br>important<br>that<br>they<br>all<br>work<br>similarly. |

### **Risks**

- A model returns wrong label IDs or badly formatted coordinates, and the bad data gets saved.
- A container builds fine but the model inside fails to load, so CVAT just gets a generic error without a useful message.
- Running multiple GPU models at the same time eats up all GPU memory and crashes the containers.
- A model takes too long to respond, the request times out without an error message, and the user is left wondering what happened.

# **Test Strategy**

## **Overall Testing Approach**

Our testing approach focuses on validating the serverless AI model integration pipeline from a system and component level perspective. We will use a range of testing types. This will be a combination of functional, integration, performance, and error handling tests to ensure the component behaves correctly under both normal and edge case conditions. The testing will simulate real world scenarios where CVAT invokes AI models through serverless APIs and processes their outputs into annotations.

## **Mapping test types to quality attributes**

CS 4223 Software Quality and Testing - Spring 2026

Ticket 1: Software Test Plan

Wed, April 1, 2026

● **Functional Testing (Reliability, Correctness)**

Ensures that models are correctly invoked and returns usable annotation outputs.

● **Integration Testing (Compatibility, Maintainability)**

Verifies communication between CVAT, serverless APIs, and AI models.

● **Performance Testing (Efficiency, Scalability)**

Measures response time, latency, and system behavior under load.

● **Error Handling Testing (Robustness, Reliability)**

Tests system behavior during failures such as timeouts, invalid responses, or API errors.

● **Security Testing (Security)**

Ensures safe API interactions and protection of data during model invocation.

## **Considerations**

● **Black-box Testing:**

Will focus on validating inputs and outputs without knowledge of internal implementation, such as verifying correct annotations are returned for given inputs.

● **White-box Testing:**

Examines internal logic such as API request handling, response parsing, and error handling within the integration layer.

● **Object-Oriented Testing:**

Ensures that modular components interact correctly and follow proper abstraction and interface design.

## **Verification & Validation Approach**

### **How verification and validation will be conducted**

Verification employs a multi-layered approach testing components individually and integrated. Verification testing confirms implementation meets requirements via:

- 1. Unit Testing: Isolated testing of LambdaGateway, LambdaFunction, LambdaQueue, and DetectionResultConverter using Django's test framework, validating internal logic, parameter validation, and data transformation.
- 2. Integration Testing: End-to-end verification of CVAT-Nuclio communication, including function discovery, HTTP request/response formats for all four function types (detector, interactor, tracker, reid), and base64 image encoding.
- 3. API Contract Testing: Validation of REST endpoints (/api/lambda/functions, /api/lambda/requests) for proper authentication, authorization, and error handling.

Validation testing ensures the system meets user needs:

CS 4223 Software Quality and Testing - Spring 2026

Ticket 1: Software Test Plan

Wed, April 1, 2026

- 1. Functional Validation: Confirming AI models produce correct, usable annotations (bounding boxes, masks, tracks) aligning with ground truth.
- 2. Performance Validation: Measuring response times to ensure interactive requirements (< 2-3 seconds per image) and evaluating batch processing scalability.
- 3. Error Condition Validation: Testing failure scenarios (timeouts, invalid responses, connection failures) for graceful degradation and clear error messages.

## **Alignment with the software lifecycle**

- **●** Continuous Integration: Automated tests run on every code change via pytest/GitHub Actions.
- **●** Model Deployment Phase: New AI models validated with standardized test datasets before user availability.
- **●** Release Testing: Comprehensive regression testing before each release.
- **●** Maintenance Phase: Periodic re-validation after infrastructure updates (Nuclio versions, dependencies).

### **Traceability to requirements or expected behavior**

- 1. Requirement Mapping: Tests verify CVAT correctly discovers functions, invokes them with proper parameters, and processes responses into valid annotations.
- 2. Quality Attribute Coverage: Direct addressing of four critical attributes:
  - *Correctness*: Annotation format, coordinate accuracy, label mapping
  - *Reliability*: Error handling, timeout recovery, consistent availability
  - *Performance*: Response latency and throughput under load
  - *Interoperability*: Consistent behavior across AI frameworks (PyTorch, TensorFlow, OpenVINO)
- 3. Risk Mitigation: Tests target identified quality risks: error messages for failed model loading, GPU memory management under concurrent loads, timeout handling with clear user feedback.

The implementation leverages CVAT's test infrastructure with mocked Nuclio responses, enabling comprehensive verification without actual AI model deployments, ensuring efficient CI/CD integration with high coverage of the serverless AI pipeline.

# **Test Environment**

Tools & Frameworks:

- pytest for unit and integration tests (as used in cvat/apps/lambda\_manager/tests/)
- Django's test framework (ApiTestBase, ForceLogin utilities from engine.tests.utils)
- REST API testing via curl or direct HTTP calls (Django test client)
- Docker Compose for local Nuclio serverless setup

CS 4223 Software Quality and Testing - Spring 2026

Ticket 1: Software Test Plan

Wed, April 1, 2026

- nuctl (Nuclio CLI v1.15.9) for function deployment
- requests library for mocking Nuclio responses

#### Test Data & Fixtures:

- Sample images (small, medium, large sizes) generated via generate\_image\_file utility
- Mock Nuclio function responses (JSON) to simulate detector/interactor/tracker/reid output
- Test function IDs matching CVAT's function type taxonomy:
  - Detector: test-openvino-omz-public-yolo-v3-tf
  - Interactor: test-openvino-dextr
  - Tracker: test-pth-foolwood-siammask
  - Reid: test-openvino-omz-intel-person-reidentification-retail-0300
- Edge cases: invalid function IDs, missing response data, malformed JSON

#### Configuration:

- Local Docker Compose environment with CVAT backend + Nuclio containers
- Mocked Nuclio HTTP responses via unittest.mock (no GPU required for unit tests)
- Real Nuclio setup on GPU for performance validation (requires Nvidia driver 450.80.02+)
- Authenticated test users via ForceLogin for permission testing

# **Test Coverage & Metrics**

#### Coverage Criteria:

- Code Coverage: Aim for 80%+ line coverage on lambda\_manager/ (views.py, serializers.py, models.py)
- API Coverage: Both endpoints tested for success and error paths:
  - /api/lambda/functions (function discovery and listing)
  - /api/lambda/requests (function invocation and result retrieval)
- Function Type Coverage: All 4 function types (detector, interactor, tracker, reid) tested with mock responses
- Error Path Coverage: All identified risks explicitly tested:
  - Malformed function responses (missing fields, wrong coordinate formats)
  - Timeout scenarios (using mock delays)
  - Invalid model load states (testing error state transitions)
  - Non-unique or missing labels

#### Metrics to Evaluate Test Effectiveness:

- 1. API Response Correctness (Correctness)
  - Metric: % of API responses matching expected schema
  - Target: 100% of responses include required fields (id, kind, labels\_v2, description, name)
    - Measurement: Validate response JSON against schema in each test case

CS 4223 Software Quality and Testing - Spring 2026

Ticket 1: Software Test Plan

Wed, April 1, 2026

- Example: Detector response must include min\_pos\_points, tracker must include supported\_shape\_types
- 2. Function Type Handling (Reliability & Interoperability)
  - Metric: Consistent behavior across all 4 function types
  - Target: Same test suite passes for detector, interactor, tracker, reid
  - Measurement: Run identical test patterns against each function type, verify uniform response format
    - Failure indicator: Different error handling or response format by type
- 3. Error Recovery (Reliability)
  - Metric: % of failed requests that return clear error messages (vs. silent failures)
  - Target: 100% of failures surface actionable HTTP status codes (4xx/5xx) with error details
    - Measurement: Log inspection and status code validation after fault injection
    - Example: Model load failure returns 500 with error message, not a null response
- 4. Permission & Authentication (Security)
  - Metric: Unauthorized requests rejected consistently
  - Target: Unauthenticated requests return 401; non-owner requests return 403
  - Measurement: Test with and without ForceLogin, verify expected status codes
  - Coverage: Both GET (function discovery) and POST (function invocation)
- 5. Performance Validation (Performance)
  - Metric: Inference latency under mocked conditions
  - Target: Mock-based invocation completes in <500ms (excludes actual model inference)
  - Measurement: Time HTTP round-trip from CVAT to mocked Nuclio endpoint
  - Note: Real inference latency depends on model + GPU and is tested in integration environment
  - 6. Mock Fidelity (Testing Confidence)
    - Metric: Coverage of Nuclio response edge cases
    - Target: Test cases cover both success and failure response structures
    - Measurement: Compare mock responses against real Nuclio function output samples
  - Example: Test both "response\_data present" and "response\_data missing" for reid functions

# **Regression & Nonfunctional Testing Strategy**

## **Regression testing approach**

For CVAT, the regression testing strategy will focus on making sure updates do not break the platform's core workflows, especially task and project creation, annotation editing, job assignment, review mode, dataset import/export, and API behavior. Because CVAT supports collaborative annotation, QA/review workflows, and automated annotation tools, regression testing should be risk-based and run after bug fixes, feature changes, dependency updates, and

CS 4223 Software Quality and Testing - Spring 2026

Ticket 1: Software Test Plan

Wed, April 1, 2026

UI or backend modifications. Automated regression tests should be used for stable and repeatable checks, such as REST API behavior, permission handling, and import/export pipelines, while manual regression testing should still be used for annotation drawing, editing, and review interactions since those are heavily visual and the most used thing by the users.

### **Planned nonfunctional tests**

The non-functional testing strategy for CVAT should include performance, load, security, usability, reliability, and compatibility testing. Performance and load testing should evaluate how well CVAT handles large annotation tasks, multiple users, and repeated save or export operations. Security testing should verify authentication, authorization, and safe handling of uploaded data and API access. Usability testing is important because annotators and reviewers must work efficiently inside the interface, while reliability testing should confirm that long annotation sessions do not result in crashes or data loss, since data is the most important product of the site. Compatibility testing should also confirm that CVAT behaves correctly across supported browsers, deployments, and connected tools such as its SDK and CLI.

# **Limitations & Risks**

## **Known Limitations**

Since this test plan focuses on the backend and integration side of CVAT's serverless AI pipeline, and not the frontend UI, issues with how annotations are displayed, edited, or interacted with in the interface may not be caught here.

A lot of the testing relies on mocked Nuclio responses instead of running real models from the serverless directory. While this makes testing faster and easier to control, it does not fully reflect how models behave when they are actually deployed in Docker containers and called through Nuclio. This is especially important for things like model accuracy, inference time, and GPU usage.

The testing environment is based on a local Docker Compose setup, which is how CVAT is typically run in development. However, this setup is much simpler than a real deployment where multiple users, larger datasets, and distributed resources are involved. Because of this, performance and scalability results may not fully match real-world usage.

GPU-based testing is also limited by available hardware. CVAT supports running multiple serverless models at once, but we may not be able to fully test scenarios where several models compete for GPU resources at the same time. This can lead to issues such as memory exhaustion, or container crashes that are harder to reproduce locally.

Lastly, the test plan assumes that all serverless functions follow the expected request and response format. Also, CVAT supports models built within different frameworks like PyTorch, TensorFlow, and OpenVINO, and small differences between them can cause inconsistencies. If a function returns slightly incorrect data, it may not always be caught unless we specifically test for that case.

Group L CS 4223 Software Quality and Testing - Spring 2026 Ticket 1: Software Test Plan

Wed, April 1, 2026

### **Potential Challenges and Mitigation Strategies**

One challenge is handling inconsistent or malformed responses from serverless functions. Since CVAT expects a specific JSON structure when it comes to model output into annotations, even small issues in formatting can break the pipeline. In order to handle this, tests include schema validation and checks for required fields before results are accepted.

Another challenge is performance variability across different models. CVAT supports a wide range of models, from lightweight detectors to more complex segmentation and tracking models, and they do not all act the same in terms of speed or resource usage. In order to address this, we separate mocked performance testing from real model testing and set clear expectations for both.

Running multiple models at the same time is also challenging, especially with GPU-backed functions. Since each model runs in its own container, resource usage can add up quickly and cause failures. We can mitigate this by testing under simulated load and monitoring how the system behaves as more functions are invoked.

There is also a risk of silent failures where when the model fails, it does not return a clear error through the API. This can make it hard for users to understand what went wrong. To help reduce this risk, tests check that all failure cases return proper HTTP status codes and meaningful error messages instead of just failing silently.

Lastly, keeping behavior consistent across all supported model types is a challenge. Even though they are all exposed through the same serverless interface, they have different inputs and outputs. To handle this, we can run the same integration tests across all function types to make sure that they behave consistently when used within CVAT.