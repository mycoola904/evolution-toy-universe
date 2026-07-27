$ErrorActionPreference = "Stop"

$Repo = "mycoola904/evolution-toy-universe"

function Ensure-GhInstalled {
    try {
        $null = gh --version
    } catch {
        throw "GitHub CLI (gh) is not installed. Install with: winget install --id GitHub.cli"
    }
}

function Ensure-GhAuth {
    try {
        gh auth status | Out-Null
    } catch {
        Write-Host "GitHub CLI is not authenticated. Starting login..."
        gh auth login
    }
}

function New-LabelIfMissing {
    param(
        [string]$Name,
        [string]$Color,
        [string]$Description
    )
    gh label create $Name --repo $Repo --color $Color --description $Description 2>$null | Out-Null
}

function Get-Milestones {
    gh api "repos/$Repo/milestones?state=all&per_page=100" | ConvertFrom-Json
}

function New-MilestoneIfMissing {
    param(
        [string]$Title,
        [string]$Description
    )
    $existing = Get-Milestones | Where-Object { $_.title -eq $Title }
    if (-not $existing) {
        gh api -X POST "repos/$Repo/milestones" -f title="$Title" -f description="$Description" | Out-Null
        Write-Host "  + milestone: $Title"
    } else {
        Write-Host "  = milestone exists: $Title"
    }
}

function New-Issue {
    param(
        [string]$Title,
        [string]$Body,
        [string[]]$Labels,
        [string]$Milestone
    )

    $labelArgs = @()
    foreach ($l in $Labels) {
        $labelArgs += @("--label", $l)
    }

    gh issue create `
      --repo $Repo `
      --title $Title `
      --body $Body `
      @labelArgs `
      --milestone $Milestone | Out-Null

    Write-Host "  + issue: $Title"
}

Ensure-GhInstalled
Ensure-GhAuth

Write-Host "Creating labels (idempotent)..."
New-LabelIfMissing "type:feature" "1D76DB" "Feature work"
New-LabelIfMissing "type:infra"   "5319E7" "Infrastructure / engineering systems"
New-LabelIfMissing "type:ui"      "0E8A16" "User interface / visualization"
New-LabelIfMissing "type:research" "FBCA04" "Research / experiment-oriented work"

New-LabelIfMissing "priority:p0"  "B60205" "Highest priority"
New-LabelIfMissing "priority:p1"  "D93F0B" "High priority"
New-LabelIfMissing "priority:p2"  "FBCA04" "Medium priority"

New-LabelIfMissing "phase:v1"     "0052CC" "Version 1 milestone"
New-LabelIfMissing "phase:v2"     "006B75" "Version 2 milestone"
New-LabelIfMissing "phase:v3"     "0B7285" "Version 3 milestone"
New-LabelIfMissing "phase:v4"     "2F9E44" "Version 4 milestone"
New-LabelIfMissing "phase:v5"     "5F3DC4" "Version 5 milestone"
New-LabelIfMissing "phase:v6"     "C2255C" "Version 6 milestone"
New-LabelIfMissing "phase:future" "6A737D" "Future / stretch ideas"

Write-Host "Creating milestones..."
New-MilestoneIfMissing "V1: Minimal Living Universe" "Closed-loop deterministic simulation where evolution can begin."
New-MilestoneIfMissing "V2: Better Observation" "Tools to inspect, replay, and analyze simulation behavior."
New-MilestoneIfMissing "V3: Richer Environment" "More varied world dynamics and resource/ecology context."
New-MilestoneIfMissing "V4: Richer Organisms" "Higher organism complexity and adaptive capabilities."
New-MilestoneIfMissing "V5: Ecosystems" "Emergent ecological interactions and trophic dynamics."
New-MilestoneIfMissing "V6: Experiments Platform" "Use simulator as experimental platform with controlled scenarios."
New-MilestoneIfMissing "Future / Stretch" "Out-of-scope ideas for later exploration."

Write-Host "Creating V1 issues..."
New-Issue "[V1] Simulation Tick Loop with Deterministic Seed Control" @"
## Summary
Implement a continuous fixed-step simulation loop where runs are reproducible with the same random seed.

## Acceptance Criteria
- [ ] Simulation loop runs continuously for configurable tick counts.
- [ ] Random seed is configurable via CLI/config.
- [ ] Running twice with the same seed yields identical state snapshots for N ticks.
- [ ] Determinism test is added to CI/local test suite.

## Notes
This is a prerequisite for most V1 functionality.
"@ @("phase:v1","type:infra","priority:p0") "V1: Minimal Living Universe"

New-Issue "[V1] Implement Toroidal World Topology" @"
## Summary
Implement wrap-around world boundaries on both axes.

## Acceptance Criteria
- [ ] Positions wrap correctly at all boundaries.
- [ ] Movement across each edge re-enters from opposite side.
- [ ] Unit tests cover edge/corner wrapping cases.
"@ @("phase:v1","type:feature","priority:p0") "V1: Minimal Living Universe"

New-Issue "[V1] Environmental Energy Generation System" @"
## Summary
Implement environmental energy spawning/regeneration model.

## Acceptance Criteria
- [ ] Energy generation model is configurable.
- [ ] Energy is spawned/regenerated during simulation ticks.
- [ ] Energy distribution is visible via debug output or UI overlay.
"@ @("phase:v1","type:feature","priority:p0") "V1: Minimal Living Universe"

New-Issue "[V1] Organism Core Model (State + Lifecycle Fields)" @"
## Summary
Define organism state model (position, energy, genome, neural state, lifecycle fields).

## Acceptance Criteria
- [ ] Organism data model includes core fields.
- [ ] Lifecycle transitions are explicitly represented.
- [ ] Model supports reproduction/death flow integration.
"@ @("phase:v1","type:feature","priority:p0") "V1: Minimal Living Universe"

New-Issue "[V1] Neural Network Execution for Action Selection" @"
## Summary
Execute neural forward pass each tick to map sensor inputs to actions.

## Acceptance Criteria
- [ ] Sensor -> NN -> action pipeline is implemented.
- [ ] Action outputs are consumed by movement/behavior update.
- [ ] Basic tests validate action output range/shape.
"@ @("phase:v1","type:feature","priority:p0") "V1: Minimal Living Universe"

New-Issue "[V1] Energy Accounting (Metabolism, Movement Cost, Intake)" @"
## Summary
Track all energy inflows/outflows per organism each tick.

## Acceptance Criteria
- [ ] Metabolic drain is applied each tick.
- [ ] Movement/behavior costs are applied.
- [ ] Energy intake from environment is applied.
- [ ] Net energy change is traceable/debuggable.
"@ @("phase:v1","type:feature","priority:p0") "V1: Minimal Living Universe"

New-Issue "[V1] Reproduction Mechanics (Asexual Baseline)" @"
## Summary
Implement baseline reproduction when threshold conditions are met.

## Acceptance Criteria
- [ ] Reproduction trigger conditions are configurable.
- [ ] Offspring creation works and inherits parent genome.
- [ ] Parent/offspring energy split or cost model is defined and applied.
"@ @("phase:v1","type:feature","priority:p0") "V1: Minimal Living Universe"

New-Issue "[V1] Genome Mutation Engine" @"
## Summary
Implement mutation operator(s) on reproduction with configurable mutation rate.

## Acceptance Criteria
- [ ] Mutation rate is configurable.
- [ ] Mutation modifies genome while preserving validity constraints.
- [ ] Mutation events are observable in logs/stats.
"@ @("phase:v1","type:feature","priority:p0") "V1: Minimal Living Universe"

New-Issue "[V1] Death and Removal Rules" @"
## Summary
Define death conditions and safely remove dead organisms from simulation state.

## Acceptance Criteria
- [ ] Death conditions (e.g., <=0 energy) are enforced.
- [ ] Dead organisms are removed without corrupting iteration/state.
- [ ] Death events are countable/observable.
"@ @("phase:v1","type:feature","priority:p0") "V1: Minimal Living Universe"

New-Issue "[V1] Basic UI Visualization (World + Organisms + Time)" @"
## Summary
Create minimal visualization to observe simulation state over time.

## Acceptance Criteria
- [ ] World and organism positions are rendered.
- [ ] Tick/time progression is visible.
- [ ] Pause/resume and step controls exist (or documented interim equivalent).
"@ @("phase:v1","type:ui","priority:p0") "V1: Minimal Living Universe"

New-Issue "[V1] Population Dynamics Telemetry (Minimum)" @"
## Summary
Expose core population metrics to support observing evolutionary dynamics.

## Acceptance Criteria
- [ ] Population count over time is recorded.
- [ ] Birth/death counts are available.
- [ ] Metrics are viewable via UI panel or logs.
"@ @("phase:v1","type:feature","priority:p1") "V1: Minimal Living Universe"

New-Issue "[V1] Definition-of-Done Validation Suite" @"
## Summary
Create validation checklist/tests for V1 completion criteria from docs/11-roadmap.md.

## Acceptance Criteria
- [ ] Continuous simulation run validated.
- [ ] Organisms consume energy.
- [ ] Organisms move according to NN outputs.
- [ ] Organisms reproduce.
- [ ] Mutation occurs.
- [ ] Organisms die.
- [ ] Population dynamics observable.
- [ ] Simulations repeat with same seed.
"@ @("phase:v1","type:infra","priority:p0") "V1: Minimal Living Universe"

function New-PhaseIssues {
    param(
        [string]$PhaseTag,
        [string]$Milestone,
        [string[]]$Titles
    )

    foreach ($t in $Titles) {
        $priority = if ($PhaseTag -eq "v2" -or $PhaseTag -eq "v3") { "priority:p1" } else { "priority:p2" }
        $type = if ($PhaseTag -eq "v6") { "type:research" } else { "type:feature" }

        New-Issue "[$($PhaseTag.ToUpper())] $t" @"
## Summary
Roadmap $($PhaseTag.ToUpper()) feature: $t

## Acceptance Criteria
- [ ] Design impact documented.
- [ ] Implemented and integrated into simulation/runtime.
- [ ] Observable behavior and/or telemetry added.
"@ @("phase:$PhaseTag",$type,$priority) $Milestone
    }
}

Write-Host "Creating V2 issues..."
New-PhaseIssues "v2" "V2: Better Observation" @(
"Genome Viewer UI",
"Neural Network Viewer UI",
"Population Graphs Dashboard",
"Species Clustering Prototype",
"Simulation Statistics Module",
"Replay Recording + Playback",
"Simulation Speed Controls (x1/x10/x100)",
"Save/Load Experiment Snapshots"
)

Write-Host "Creating V3 issues..."
New-PhaseIssues "v3" "V3: Richer Environment" @(
"Terrain Type System",
"Resource Gradient Model",
"Seasonal Cycle Mechanics",
"Environmental Hazards",
"Resource Regeneration Strategies",
"Multiple Energy Source Types"
)

Write-Host "Creating V4 issues..."
New-PhaseIssues "v4" "V4: Richer Organisms" @(
"Memory Neuron Support",
"Additional Sensor Channels",
"Organism Communication Signals",
"Lifespan Constraints",
"Larger Genome Encoding",
"Developmental Gene Effects"
)

Write-Host "Creating V5 issues..."
New-PhaseIssues "v5" "V5: Ecosystems" @(
"Predation Interaction Rules",
"Scavenging Mechanics",
"Waste Product System",
"Food Chain Dynamics",
"Cooperative Behavior Primitives",
"Ecological Niche Detection Metrics"
)

Write-Host "Creating V6 issues..."
New-PhaseIssues "v6" "V6: Experiments Platform" @(
"Experiment Runner: Mutation Rate Sweep",
"Experiment Runner: Resource Abundance Sweep",
"Experiment Runner: Neural Size Sweep",
"Population Bottleneck Scenario Harness",
"Catastrophic Event Scenario Harness",
"Strategy Competition Benchmark Suite",
"Experiment Results Export + Comparison Reports"
)

Write-Host ""
Write-Host "Done. Open issues:"
gh issue list --repo $Repo --state open --limit 200