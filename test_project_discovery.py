#!/usr/bin/env python3
"""
Test project discovery capabilities
"""

import asyncio
import logging
from pathlib import Path
from src.learning.project_discovery import ProjectDiscoveryLearner

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    print("=== Sakana Project Discovery Test ===\n")
    
    # Create project discovery learner
    # Start with your home directory
    learner = ProjectDiscoveryLearner(base_path="~")
    
    # Discover projects in your nicol folder
    nicol_path = Path.home() / "nicol"
    if not nicol_path.exists():
        # Try other common locations
        nicol_path = Path.home()
        print(f"Note: Searching in {nicol_path} instead")
    
    print(f"Discovering projects in: {nicol_path}")
    print("This will explore directories and learn what projects you have...\n")
    
    # Run discovery
    projects = await learner.discover_projects(str(nicol_path))
    
    print(f"\n✓ Discovered {len(projects)} projects!")
    
    # Show discovered projects
    if projects:
        print("\nProjects found:")
        for i, project in enumerate(projects[:10], 1):  # Show first 10
            print(f"\n{i}. {project.name}")
            print(f"   Path: {project.path}")
            print(f"   Type: {project.type}")
            print(f"   Capabilities: {', '.join(project.capabilities[:5])}")
            if len(project.capabilities) > 5:
                print(f"   ... and {len(project.capabilities) - 5} more capabilities")
        
        if len(projects) > 10:
            print(f"\n... and {len(projects) - 10} more projects")
        
        # Evolve understanding of the most interesting project
        most_capable = max(projects, key=lambda p: len(p.capabilities))
        print(f"\n🧬 Evolving deeper understanding of: {most_capable.name}")
        await learner.evolve_project_understanding(most_capable)
        print(f"   Enhanced capabilities: {len(most_capable.capabilities)}")
    
    # Generate report
    print("\n" + "="*50)
    print(learner.get_project_report())
    
    print("\n💡 The system will remember these projects and learn more about them over time!")
    print("   Each time you use it, it discovers new capabilities and patterns.")

if __name__ == "__main__":
    asyncio.run(main())