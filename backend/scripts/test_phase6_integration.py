"""Quick test for Phase 6 integration."""

import sys
sys.path.insert(0, 'd:\\testing2\\backend')

try:
    # Test Phase 6 import
    from app.retrieval.phase6_integration import (
        Phase6IntelligenceEngine,
        IntelligentRecommendation,
        run_enhanced_pipeline,
        Phase6EvaluationFramework,
    )
    print("✓ Phase 6 integration modules imported successfully")

    # Test engine creation
    engine = Phase6IntelligenceEngine()
    print("✓ Phase6IntelligenceEngine created successfully")

    # Test evaluation framework
    evaluator = Phase6EvaluationFramework()
    print("✓ Phase6EvaluationFramework created successfully")

    # Test IntelligentRecommendation structure
    rec = IntelligentRecommendation(
        standard_id="test-id",
        standard_number="IS TEST:2020",
        title="Test Standard",
        data={}
    )
    print("✓ IntelligentRecommendation created successfully")

    print("\n✅ All Phase 6 integration tests passed!")

except Exception as e:
    print(f"❌ Phase 6 integration test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)