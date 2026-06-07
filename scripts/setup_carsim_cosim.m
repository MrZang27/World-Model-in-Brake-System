function info = setup_carsim_cosim(seedModelPath, options)
%SETUP_CARSIM_COSIM Inspect a CarSim seed model and build project assets.

arguments
    seedModelPath (1,1) string = fullfile("models", "carsim_seed_model.slx")
    options.Overwrite (1,1) logical = false
end

projectRoot = fileparts(fileparts(mfilename("fullpath")));
cd(projectRoot);
addpath(fullfile(projectRoot, "src"));
addpath(fullfile(projectRoot, "scripts"));

if ~isfile(seedModelPath)
    error("CarSim:MissingSeedModel", ...
        "Missing %s.\n" + ...
        "Configure the CarSim Run imports/exports, use 'Send to Simulink', " + ...
        "and save the generated model at that path.", seedModelPath);
end

reportPath = fullfile(projectRoot, "results", "carsim_interface_report.tsv");
report = inspect_carsim_interface(seedModelPath, reportPath);
info = create_carsim_brake_cosim_model(seedModelPath, ...
    OutputModelPath=fullfile(projectRoot, "models", "carsim_brake_cosim.slx"), ...
    Overwrite=options.Overwrite);
manifest = generate_carsim_case_manifest( ...
    fullfile(projectRoot, "config", "carsim_case_manifest.csv"));

info.interfaceReport = report;
info.manifest = manifest;
fprintf("\nCarSim project setup complete.\n");
fprintf("Next: fill config/carsim_case_manifest.csv run_file values.\n");
end
