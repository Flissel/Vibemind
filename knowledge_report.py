#!/usr/bin/env python3
"""
View accumulated knowledge report
"""

from src.learning.knowledge_accumulator import KnowledgeAccumulator

def main():
    print("=== Sakana Knowledge Report ===\n")
    
    # Load knowledge accumulator
    knowledge = KnowledgeAccumulator()
    
    # Generate and display report
    report = knowledge.export_knowledge_report()
    print(report)
    
    # Show additional insights
    stats = knowledge.get_discovery_stats()
    
    if stats['knowledge_growth_trend'] == 'saturating':
        print("\n💡 Tip: Knowledge growth is saturating. Most common commands have been discovered.")
        print("   Consider exploring specialized tools or platform-specific commands.")
    else:
        print("\n🌱 Knowledge is still growing! Keep using the assistant to discover more.")
    
    # Show unexplored areas
    suggestions = knowledge.suggest_unexplored_areas()
    if suggestions:
        print("\n🔍 Unexplored Areas:")
        for suggestion in suggestions[:3]:
            print(f"   - {suggestion}")

if __name__ == "__main__":
    main()