import os
import subprocess

def main():
    BASE_PATH = os.getenv('BASE_PATH')
    STAC_ASSET_GENERATOR_TIMEOUT = os.getenv('STAC_ASSET_GENERATOR_TIMEOUT')
    STAC_HOST = os.getenv('STAC_HOST')

    if BASE_PATH is None:
        print("[INFO] BASE_PATH environment variable not set. Using blank value for BASE_PATH")
        BASE_PATH = ""
    else:
        print("[INFO] Using BASE_PATH=", BASE_PATH)

    if STAC_ASSET_GENERATOR_TIMEOUT is None:
        print("[INFO] STAC_ASSET_GENERATOR_TIMEOUT environment variable not set. Using '30'")
        STAC_ASSET_GENERATOR_TIMEOUT = "30"
    else:
        print("[INFO] Using STAC_ASSET_GENERATOR_TIMEOUT=", STAC_ASSET_GENERATOR_TIMEOUT)
    if STAC_HOST is None:
        print("[INFO] STAC_HOST environment variable not set. Using '127.0.0.1'")
        STAC_HOST = "127.0.0.1"
    else:
        print("[INFO] Using STAC_HOST=", STAC_HOST)

    os.chdir(BASE_PATH + "/populator")

    #replace STAC host name of collection processor
    subprocess.run(['sed -i "/stac_host:/c\stac_host: {}" collections.yaml'.format(STAC_HOST)], shell=True)
    
    # create collections
    subprocess.run(['python3 ./collection_processor.py collections.yaml'], shell=True)
    
    os.chdir(BASE_PATH + "/stac-generator-example")
    
    # replace STAC host name of asset generators
    subprocess.run(['sed -i "/host:/c\      host: {}" conf/thredds-cmip6-asset-generator.yaml'.format(STAC_HOST)], shell=True)
    subprocess.run(['sed -i "/host:/c\      host: {}" conf/thredds-cmip5-asset-generator.yaml'.format(STAC_HOST)], shell=True)
    
    print("Running STAC asset generator for {} seconds...".format(STAC_ASSET_GENERATOR_TIMEOUT))

    # add items
    cmip6 = subprocess.run(['timeout {} bash -c "python3 -m stac_generator.scripts.stac_generator conf/thredds-cmip6-asset-generator.yaml" \
    || true'.format(STAC_ASSET_GENERATOR_TIMEOUT)], shell=True, capture_output=True, text=True)
    print(cmip6.stdout)

    cmip5 = subprocess.run(['timeout {} bash -c "python3 -m stac_generator.scripts.stac_generator conf/thredds-cmip5-asset-generator.yaml" \
    || true'.format(STAC_ASSET_GENERATOR_TIMEOUT)], shell=True, capture_output=True, text=True)    
    print(cmip5.stdout)
    
    os.chdir(BASE_PATH + "/populator")

    # update collection summaries
    subprocess.run(['python3 collection_processor.py collections.yaml'], shell=True)

    print("STAC asset generator ran for {} seconds. Exiting.".format(STAC_ASSET_GENERATOR_TIMEOUT))


if __name__ == "__main__":
    main()
